// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Timestamper {

    address owner = msg.sender;   

    modifier onlyOwner(){
        require(msg.sender == owner);
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    event Timestamp(uint256 indexed id_hash, uint256 indexed value_hash);

    function timestamp(uint256 id_hash, uint256 value_hash) public onlyOwner {
        emit Timestamp(id_hash, value_hash);
    }

    function batchTimestamp(uint256[] memory id_hashes, uint256[] memory value_hashes) public onlyOwner {
        for (uint256 i = 0; i < id_hashes.length; i++) {
            emit Timestamp(id_hashes[i], value_hashes[i]);
        }
    }
}