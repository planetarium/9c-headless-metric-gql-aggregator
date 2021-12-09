FROM python:3.10

ADD . .

RUN python -m pip install poetry
RUN poetry install

CMD ["poetry", "run", "uvicorn", "app:app", "--port=80", "--host=0.0.0.0"]