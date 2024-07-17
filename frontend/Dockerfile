FROM node:20.11.1-alpine3.18

WORKDIR /react-onto-frontend/

COPY public/ /react-onto-frontend/public
COPY src/ /react-onto-frontend/src
COPY package.json /react-onto-frontend/

RUN npm install
CMD ["npm", "start"]
