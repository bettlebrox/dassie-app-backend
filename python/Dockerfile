# Use the official AWS Lambda Python 3.12 base image
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory
WORKDIR /var/task

# Copy the requirements file into the container
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the dependencies
RUN pip install -r requirements.txt --no-cache-dir

# Copy the rest of your application code
COPY lambda/ ${LAMBDA_TASK_ROOT}

COPY --from=public.ecr.aws/datadog/lambda-extension:latest /opt/. /opt/
CMD ["datadog_lambda.handler.handler"]
