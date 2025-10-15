# Use the official Argilla server image
FROM argilla/argilla-server:latest

# Copy the built frontend with Korean translation to both locations
COPY argilla-frontend/dist /opt/argilla/frontend
COPY argilla-frontend/dist /opt/venv/lib/python3.13/site-packages/argilla_server/static

# The server will serve the custom frontend
ENV ARGILLA_HOME_PATH=/var/lib/argilla

EXPOSE 6900

# Use the default entrypoint from the base image