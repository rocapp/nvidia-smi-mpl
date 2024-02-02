from fastapi import FastAPI
from fastapi.routing import APIRouter
from nvidia_smi_mpl.main import get_nvidia_smi_data, asdict


def setup_server(host='127.0.0.1', port=9000):
    app = FastAPI(title='NVIDIA GPU Metrics Visualizer')


    @app.get('/')
    async def root():
        return {'message': 'NVIDIA GPU Metrics Visualizer API is running.'}


    router = APIRouter(prefix = '/v1')


    @router.get('/metrics')
    async def metrics():
        return asdict(get_nvidia_smi_data())


    app.include_router(router)


    def start_server():
        import uvicorn
        uvicorn.run(app, host=host, port=port)

    return start_server()


if __name__ == '__main__':
    setup_server()