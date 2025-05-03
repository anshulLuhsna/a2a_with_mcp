        # Use an official Python runtime as a parent image
        FROM python:3.12-slim

        # Set the working directory in the container
        WORKDIR /app

        # Copy the requirements file into the container
        COPY orchestrator_agent/requirements.txt .

        # Install any needed packages specified in requirements.txt
        # --no-cache-dir reduces image size
        RUN pip install --no-cache-dir -r requirements.txt

        # Copy the agent's code and the common library
        # Assumes 'common' is one level up relative to the Dockerfile context
        COPY orchestrator_agent/ .
        COPY common/ common/

        # Make port 8000 available to the world outside this container (mapped in docker-compose)
        EXPOSE 8000

        # Define environment variables (will be overridden by docker-compose)
        ENV PORT=8000
        ENV HOST=0.0.0.0
        # Add other ENV vars needed by the orchestrator (Agent URLs, API Keys - set in compose)

        # Run the agent as a module when the container launches
        CMD ["python", "-m", "orchestrator_agent"]