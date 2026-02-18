FROM node:20.11.1-alpine3.18

WORKDIR /app

COPY package*.json ./

RUN npm install --legacy-peer-deps

COPY . .


CMD ["npm", "start"]
