# check=skip=SecretsUsedInArgOrEnv
# Ignore false-positive warning about VITE_AUTH_URL
FROM node:20.19.5 AS build

ARG VITE_PORT="8080"
ENV VITE_PORT=$VITE_PORT
ARG VITE_AUTH_URL=""
ENV VITE_AUTH_URL=$VITE_AUTH_URL
ARG VITE_BASE_PATH="http://localhost:8080"
ENV VITE_BASE_PATH=$VITE_BASE_PATH
ARG VITE_API_PATH="http://localhost:8081"
ENV VITE_API_PATH=$VITE_API_PATH

WORKDIR /app
COPY package.json package-lock.json /app/
RUN npm ci
COPY . /app/
RUN npm run build-prod

FROM nginx:1.29.1
EXPOSE 8080
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /app
# Resolve permissions issues on unprivileged setups
RUN touch /run/nginx.pid
RUN chmod -R g+rw /var/cache/nginx/ /run/nginx.pid