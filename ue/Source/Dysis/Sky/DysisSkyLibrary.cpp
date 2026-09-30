#include "DysisSkyLibrary.h"
#include "DysisSkyData.generated.h"
#include "GameFramework/Actor.h"

namespace
{
	using namespace DysisSkyData;

	constexpr double Deg = UE_DOUBLE_PI / 180.0;

	// ───────── 小工具（和灰盒同名） ─────────
	double Wrap360(double A)                    // Python 的 a % 360.0：结果在 [0, 360)
	{
		double R = FMath::Fmod(A, 360.0);
		if (R < 0.0) R += 360.0;
		return R;
	}
	double AngDiff(double A, double B) { return Wrap360(Wrap360(A - B) + 540.0) - 180.0; }
	double Clamp(double X, double A, double B) { return FMath::Min(B, FMath::Max(A, X)); }
	double Lerp(double A, double B, double T) { return A + (B - A) * T; }
	bool InArc(double Az, const double (&Arc)[2])
	{
		const double A0 = Arc[0], A1 = Arc[1];
		double T = Az;
		while (T < A0) T += 360.0;
		while (T >= A0 + 360.0) T -= 360.0;
		return T <= A1;
	}

	// ───────── 每层的时间线（reference 的 LineZone / PieceZone） ─────────
	double ZoneUn(const FZoneLine& Z, double Az)
	{
		const double T = Wrap360(Az);
		return T < Z.Lo ? T + 360.0 : T;
	}
	double PieceFU(const FZoneLine& Z, double T)
	{
		if (T <= Z.Pts[0][0]) return Z.Pts[0][1];
		for (int32 I = 1; I < Z.NumPts; ++I)
		{
			if (T <= Z.Pts[I][0])
				return Z.Pts[I - 1][1] + (Z.Pts[I][1] - Z.Pts[I - 1][1]) * (T - Z.Pts[I - 1][0]) / (Z.Pts[I][0] - Z.Pts[I - 1][0]);
		}
		return Z.Pts[Z.NumPts - 1][1];
	}
	double ZoneF(const FZoneLine& Z, double Az)
	{
		double T = ZoneUn(Z, Az);
		if (InArc(Az, SEAM)) T = AngDiff(Az, (SEAM[0] + SEAM[1]) / 2.0) > 0.0 ? Z.Lo : Z.Hi;
		return Z.bPiece ? PieceFU(Z, T) : Z.H0 + Z.K * (T - Z.A0);
	}
	const FZoneLine& Floor(bool bNight, int32 Index) { return bNight ? NightZones[Index] : DayZones[Index]; }
	int32 FloorIndexOfY(double Y)                // reference 的 F.index(yy)
	{
		for (int32 I = 0; I < 4; ++I) if (F[I] == Y) return I;
		checkf(false, TEXT("DysisSkyData: stair end height %f is not in F"), Y);
		return 0;
	}

	// ───────── 屋顶环道：白天 J → 接光台，时间 H_OC → H_TOP；夜里接光台 → J → 降下来的楼梯到四层 ─────────
	double CrownDay(double Az)
	{
		const double RawAz = Wrap360(Az - J_AZ), Pc = Wrap360(CATCH_AZ - J_AZ);
		const double Psi = RawAz > 300.0 ? 0.0 : RawAz;
		return Psi <= Pc ? Lerp(H_OC, H_TOP, Psi / Pc) : H_TOP + 0.02 * FMath::Min(Psi - Pc, 12.0);
	}
	double CrownNight(double Az)
	{
		const double Back = Wrap360(CATCH_AZ - Az), Tj = Wrap360(CATCH_AZ - J_AZ), Jd = Wrap360(J_AZ - DN_FOOT);
		if (Back > 330.0) return H_TOP - 0.02 * FMath::Min(360.0 - Back, 12.0);
		if (Back <= Tj) return Lerp(H_TOP, H_J, Back / Tj);
		return Lerp(H_J, H_L3A, Clamp((Back - Tj) / Jd, 0.0, 1.0));
	}

	// ───────── 墙里的楼梯：按高度在上门、下门两处的时刻之间插值 ─────────
	const FTunnel* FindTunnel(const FString& Id)
	{
		for (const FTunnel& T : Tunnels) if (Id.Equals(T.Id, ESearchCase::CaseSensitive)) return &T;
		return nullptr;
	}
	double Tunnel(const FTunnel& T, double Y, bool bNight)
	{
		const double HTop = ZoneF(Floor(bNight, FloorIndexOfY(T.YTop)), T.TopDoor);
		const double HBot = ZoneF(Floor(bNight, FloorIndexOfY(T.YBot)), T.BotDoor);
		return Lerp(HTop, HBot, Clamp((T.YTop - Y) / (T.YTop - T.YBot), 0.0, 1.0));
	}

	double MoonBrT(const FVector& PosCm)
	{
		int32 Best = 0; double Bd = 1e18;
		for (int32 I = 0; I < NumMoonBridgePts; ++I)
		{
			const double* P = MoonBridgePtsUE[I];
			const double D = FMath::Square(P[0] - PosCm.X) + FMath::Square(P[1] - PosCm.Y) + FMath::Square(P[2] - PosCm.Z);
			if (D < Bd) { Bd = D; Best = I; }
		}
		return double(Best) / double(NumMoonBridgePts - 1);
	}

	// ───────── reference 的 _raw ─────────
	double Raw(const FString& Zone, double Az, double Y, const FVector& PosCm, bool bNight, double Sticky)
	{
		if (Zone.StartsWith(TEXT("beam:"), ESearchCase::CaseSensitive))
		{
			const FString Bid = Zone.Mid(5);
			if (Bid == TEXT("isle")) return H_I;
			if (Bid == TEXT("oculus")) return H_OC;
			if (Bid == TEXT("mirror")) return H_M;
			for (const FBeamTimeY& Ty : BeamTimeY)
				if (Bid.Equals(Ty.Id, ESearchCase::CaseSensitive))
					return Ty.H0 + (Ty.H1 - Ty.H0) * (Y - Ty.Y0) / (Ty.Y1 - Ty.Y0);   // 光路上按高度线性插值（不夹）
			return Sticky;
		}
		if (Zone.StartsWith(TEXT("tun:"), ESearchCase::CaseSensitive))
		{
			const FTunnel* T = FindTunnel(Zone.Mid(4));
			return T ? Tunnel(*T, Y, bNight) : Sticky;   // reference 遇到未知楼梯会抛 KeyError；这里按“不认识的名字”退回 Sticky
		}
		if (Zone == TEXT("L0")) return ZoneF(Floor(bNight, 0), Az);
		if (Zone == TEXT("L1")) return ZoneF(Floor(bNight, 1), Az);
		if (Zone == TEXT("L2")) return ZoneF(Floor(bNight, 2), Az);
		if (Zone == TEXT("L3")) return ZoneF(Floor(bNight, 3), Az);
		if (Zone == TEXT("crown")) return bNight ? CrownNight(Az) : CrownDay(Az);
		if (Zone == TEXT("rbridge")) return bNight ? H_J : H_OC;
		if (Zone == TEXT("ledge")) return H_M;
		if (Zone == TEXT("moonbr")) return Lerp(MOONBR_H0, MOONBR_H1, MoonBrT(PosCm));
		if (Zone == TEXT("rainbow") || Zone == TEXT("sill")) return RELIEF_H;
		if (Zone == TEXT("wfback")) return ZoneF(Floor(bNight, 0), SEAM[0] - 0.5);
		if (Zone == TEXT("gbridge") || Zone == TEXT("shadowbr") || Zone == TEXT("pav")) return bNight ? H_BR : Sticky;
		if (Zone == TEXT("out")) return bNight ? Sticky : H_I;
		return Sticky;   // pool 等
	}

	const TMap<FName, double>& ConstTable()
	{
		static const TMap<FName, double> Table = {
			{ TEXT("LAT"), LAT }, { TEXT("DEC_SUN"), DEC_SUN }, { TEXT("DEC_MOON"), DEC_MOON }, { TEXT("CEIL"), CEIL }, { TEXT("RING_Y"), RING_Y },
			{ TEXT("R_IN"), R_IN }, { TEXT("R_A"), R_A }, { TEXT("TOP_Y"), TOP_Y }, { TEXT("H_I"), H_I }, { TEXT("H_B1TOP"), H_B1TOP },
			{ TEXT("H_B2TOP"), H_B2TOP }, { TEXT("H_H0"), H_H0 }, { TEXT("H_H1"), H_H1 }, { TEXT("H_X"), H_X }, { TEXT("H_M"), H_M },
			{ TEXT("H_OC"), H_OC }, { TEXT("H_TOP"), H_TOP }, { TEXT("H_J"), H_J }, { TEXT("H_L3A"), H_L3A }, { TEXT("H_SW"), H_SW },
			{ TEXT("H_3X"), H_3X }, { TEXT("H_G"), H_G }, { TEXT("H_TW"), H_TW }, { TEXT("H_BR"), H_BR }, { TEXT("H_END"), H_END },
			{ TEXT("RELIEF_H"), RELIEF_H }, { TEXT("B1_H"), B1_H }, { TEXT("B2_H"), B2_H }, { TEXT("TWINS_Hc"), TWINS_Hc },
			{ TEXT("TWINS_Hw"), TWINS_Hw }, { TEXT("MOONBR_H0"), MOONBR_H0 }, { TEXT("MOONBR_H1"), MOONBR_H1 }, { TEXT("J_AZ"), J_AZ },
			{ TEXT("AZ_OC"), AZ_OC }, { TEXT("T_AZ"), T_AZ }, { TEXT("CATCH_AZ"), CATCH_AZ }, { TEXT("DN_FOOT"), DN_FOOT }, { TEXT("UP_SPAN"), UP_SPAN },
		};
		return Table;
	}
}

// ───────── 天：固定的倾斜圆轨道 ─────────
FVector UDysisSkyLibrary::SkyDir(double HDeg, double DecDeg)
{
	const double H = HDeg * Deg, Dec = DecDeg * Deg, Lat = LAT * Deg;
	const double E = -FMath::Cos(Dec) * FMath::Sin(H);
	const double N = FMath::Sin(Dec) * FMath::Cos(Lat) - FMath::Cos(Dec) * FMath::Cos(H) * FMath::Sin(Lat);
	const double U = FMath::Sin(Dec) * FMath::Sin(Lat) + FMath::Cos(Dec) * FMath::Cos(H) * FMath::Cos(Lat);
	return FVector(N, E, U);   // UE：X = 北，Y = 东，Z = 上
}

FVector UDysisSkyLibrary::DysisSunDir(float H) { return SkyDir(H, DEC_SUN); }
FVector UDysisSkyLibrary::DysisMoonDir(float H) { return SkyDir(double(H) - 180.0, DEC_MOON); }   // 月亮的时角比太阳晚 180°

void UDysisSkyLibrary::DysisAzAlt(FVector Dir, float& AzDeg, float& AltDeg)
{
	AzDeg = float(Wrap360(FMath::Atan2(Dir.Y, Dir.X) / Deg));
	AltDeg = float(FMath::Asin(Clamp(Dir.Z, -1.0, 1.0)) / Deg);
}

FRotator UDysisSkyLibrary::DysisLightRotation(FVector Dir)
{
	const double Az = Wrap360(FMath::Atan2(Dir.Y, Dir.X) / Deg);
	const double Alt = FMath::Asin(Clamp(Dir.Z, -1.0, 1.0)) / Deg;
	return FRotator(-Alt, Wrap360(Az + 180.0), 0.0);
}

double UDysisSkyLibrary::TimeAtD(const FString& Zone, const FVector& PosCm, bool bNight, double Sticky)
{
	const double Az = Wrap360(FMath::Atan2(PosCm.Y, PosCm.X) / Deg);
	const double Y = PosCm.Z / 100.0;
	double H = Raw(Zone, Az, Y, PosCm, bNight, Sticky);
	if (bNight) H = Clamp(H, H_TOP, H_END);   // 夜里（接住最后一缕光以后）夹在 [H_TOP, H_END]
	return H;
}

float UDysisSkyLibrary::DysisTimeAt(const FString& Zone, FVector PosCm, bool bNight, float Sticky)
{
	return float(TimeAtD(Zone, PosCm, bNight, Sticky));
}

FString UDysisSkyLibrary::DysisZoneOf(const AActor* Ground, FVector FootCm)
{
	static const FString Prefix = TEXT("DysisZone=");
	const double Y = FootCm.Z / 100.0;
	if (Ground)
	{
		for (const FName& Tag : Ground->Tags)
		{
			const FString S = Tag.ToString();
			if (!S.StartsWith(Prefix)) continue;
			const FString Zone = S.Mid(Prefix.Len());
			if (Zone != TEXT("wall")) return Zone;
			// 墙里的两段楼梯：踏步在 r 15.8–16.8，两头门口的门槛 15.5–15.8，灰盒里都算楼梯
			const double R = FMath::Sqrt(FootCm.X * FootCm.X + FootCm.Y * FootCm.Y) / 100.0;
			if (R >= 15.5 && R <= 16.8)
			{
				const double Az = Wrap360(FMath::Atan2(FootCm.Y, FootCm.X) / Deg);
				if (Az >= 250.0 && Az <= 330.0) return TEXT("tun:TS");
				if (Az >= 105.0 && Az <= 185.0) return TEXT("tun:TR");
			}
			break;   // 墙的其他地方按高度兜底
		}
	}
	// 高度兜底（灰盒 zoneOf 的最后几行）
	if (Y > RING_Y - 0.3) return TEXT("crown");
	if (Y >= F[3] - 0.3) return TEXT("L3");
	if (Y >= F[2] - 0.3) return TEXT("L2");
	if (Y >= F[1] - 0.3) return TEXT("L1");
	if (Y > -1.0) return TEXT("L0");
	return TEXT("out");
}

float UDysisSkyLibrary::DysisConst(FName Name)
{
	if (const double* V = ConstTable().Find(Name)) return float(*V);
	UE_LOG(LogTemp, Warning, TEXT("DysisConst: no constant named %s"), *Name.ToString());
	return 0.f;
}