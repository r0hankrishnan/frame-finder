# Use a Debian-based slim image, NOT alpine.
# Alpine uses musl libc, which causes painful build failures with packages that
# ship compiled C extensions (numpy, torch, psycopg2-binary). slim is Debian-based
# and compatible with your ML stack out of the box.
FROM python:3.13-slim

# Set the working directory inside the image. All subsequent commands run here,
# and COPY targets land here.
WORKDIR /app

# Copy everything from the build context (your repo) into /app in the image.
# This includes src/, app/, frontend/, data/, pyproject.toml, etc.
COPY . .

# Install your project. `pip install .` reads pyproject.toml and installs:
#   (a) all declared dependencies (fastapi, uvicorn, torch, etc.)
#   (b) your local `frame_finder` package (via the src/ layout config)
# --no-cache-dir keeps the image smaller by not caching downloaded wheels.
RUN pip install --no-cache-dir .

# Launch the app. Shell form (not exec-form array) is used deliberately so that
# $PORT — injected by Railway at runtime — gets expanded by the shell.
# --host 0.0.0.0 makes the server accept external connections (not just localhost).
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT