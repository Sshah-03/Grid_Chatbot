from app.main import create_app


def test_app_imports():
    app = create_app()
    assert app.title == "Grid Chatbot Realtime Chat API"
