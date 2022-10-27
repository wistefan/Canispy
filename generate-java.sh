#!/bin/bash

contractsFolder=${1:-./app/smartcontracts/test_deploy}

for filename in $contractsFolder/*.abi; do
    web3j generate solidity --abiFile=$filename --outputDir=build/java --package=org.fiware.aeicontract
done


