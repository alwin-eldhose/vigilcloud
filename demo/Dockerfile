# The demo app as a container image, for LKE or any other container host.
# Build it from the repo folder:  docker build -t IMAGE demo/
# Settings come from the environment when the container starts. Never copy .env into an image.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /bin/uv
WORKDIR /app
COPY app.py index.html ./
# Install the packages listed at the top of app.py, pinned to the versions uv picks on the day you build.
RUN uv export --script app.py --no-hashes -o requirements.txt \
 && uv pip install --system --no-cache -r requirements.txt
ENV PORT=80
EXPOSE 80
CMD ["python", "app.py"]
