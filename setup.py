from setuptools import setup, find_packages

setup(
    name="churchsuite-chat",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "starlette==0.41.1",
        "fastapi==0.109.0",
        "uvicorn==0.27.0",
        "python-dotenv==1.0.0",
        "openai==1.3.0",
        "httpx==0.26.0",
        "redis==5.0.1",
        "pydantic==2.5.3",
        "python-jose==3.3.0",
        "passlib==1.7.4",
        "pytest==7.4.4"
    ],
    python_requires=">=3.10",
)
