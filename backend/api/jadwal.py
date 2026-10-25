import runpy

if __name__ == "__main__":
    runpy.run_module("backend.app.jobs.jadwal", run_name="__main__", alter_sys=True)
