# 从编辑器外面把一段 Python 发进正在运行的 UE 编辑器执行（用引擎自带的 remote_execution）。
#
# 前提：项目设置 → 插件 → Python → 勾上 “Enable Remote Execution”（只在本机 127.0.0.1 上监听）。
# 用法：
#   python ue_run.py 脚本.py [参数...]     → 在编辑器里执行这个文件（参数进 sys.argv）
#   python ue_run.py -c "print(1+1)"        → 执行一段代码
# 环境变量 UE_ROOT 指向引擎目录（默认 D:/UE5/UE_5.8）。
import os, sys, time

UE_ROOT = os.environ.get("UE_ROOT", r"D:/UE5/UE_5.8")
sys.path.insert(0, os.path.join(UE_ROOT, "Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python"))
import remote_execution as rex  # noqa: E402

def main():
    if len(sys.argv) < 2:
        print("用法：python ue_run.py 脚本.py [参数...]  或  python ue_run.py -c \"代码\""); return 2
    if sys.argv[1] == "-c":
        command = sys.argv[2]
    else:
        path = os.path.abspath(sys.argv[1]).replace("\\", "/")
        args = " ".join('"%s"' % a for a in sys.argv[2:])
        command = f'{path} {args}'.strip()
    r = rex.RemoteExecution(); r.start()
    try:
        t0 = time.time()
        while not r.remote_nodes and time.time() - t0 < 15: time.sleep(0.2)
        if not r.remote_nodes:
            print("找不到编辑器：确认编辑器开着，并且打开了 Python 的 Enable Remote Execution"); return 3
        r.open_command_connection(r.remote_nodes[0]["node_id"])
        res = r.run_command(command, unattended=True, exec_mode=rex.MODE_EXEC_FILE)
        for o in res.get("output", []):
            print(o.get("output", "").rstrip())
        if not res.get("success"):
            print("执行失败：", res.get("result")); return 1
        return 0
    finally:
        r.stop()

if __name__ == "__main__":
    sys.exit(main())
