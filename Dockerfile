FROM node:12

RUN npm install -g truffle

RUN mkdir /py-contracts
WORKDIR /py-contracts
COPY ./package-lock.json /py-contracts/package-lock.json
COPY ./package.json /py-contracts/package.json
COPY ./truffle-config.js /py-contracts/truffle-config.js 
COPY ./app/smartcontracts/src/ngsi /py-contracts/contracts/
COPY ./migrations/ /py-contracts/migrations/

RUN npm install \
    && npm config set bin-links false 

RUN truffle compile 

ARG RPC_ENDPOINT
ARG RPC_PORT

ENV RPC_ENDPOINT $RPC_ENDPOINT
ENV RPC_PORT $RPC_PORT

CMD ["truffle", "migrate"]