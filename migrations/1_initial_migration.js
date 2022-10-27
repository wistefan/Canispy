const Timestamper = artifacts.require("../contracts/Timestamper.sol");

module.exports = function(deployer) {
  deployer.deploy(Timestamper);
};