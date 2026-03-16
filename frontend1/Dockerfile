# Stage 1: Build the React application
FROM node:22-bookworm-slim AS builder

WORKDIR /app

# Declare build-time arguments
ARG VITE_API_URL

# Set the environment variable for the build process
ENV VITE_API_URL=$VITE_API_URL

# Copy package files from the correct subdirectory. The build context is the project root.
COPY ./frontend1/package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy the rest of the application source code
COPY ./frontend1/ ./

# Build the application for production
RUN npm run build

# Stage 2: Serve the static files with a lightweight Nginx server
FROM nginx:stable-alpine

# Copy the build output from the builder stage to the Nginx web root
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration for a Single Page Application
COPY ./frontend1/nginx.conf /etc/nginx/conf.d/default.conf
