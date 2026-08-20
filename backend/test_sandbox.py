from app.core.sandbox import get_sandbox_manager

manager = get_sandbox_manager()
sandbox = manager.create("https://github.com/jazzband/django-silk.git")

sandbox.write_file("/workspace/repo/hello.txt", 'hello\nwith a $pecial char and "quotes"')
readback = sandbox.read_file("/workspace/repo/hello.txt")
print("written and read back:", repr(readback))

sandbox.destroy()
