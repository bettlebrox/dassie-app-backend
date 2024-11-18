# Use the official AWS Lambda Python 3.9 base image
FROM public.ecr.aws/lambda/python:3.9

# Set the working directory
WORKDIR /var/task

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt --no-cache-dir

# Copy the rest of your application code
COPY lambda/ .

# Set the CMD to use an environment variable for the handler
CMD ["${LAMBDA_FUNCTION}"]  # Update this if necessary