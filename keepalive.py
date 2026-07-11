import os
from aiohttp import web


async def _health(request):
    return web.Response(text="SOS_ELECTRO ⚡ работает", content_type="text/plain")


async def start_keepalive():
    port = int(os.environ.get("PORT", 8000))
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"✅ Keep-alive сервер запущен на порту {port}")
