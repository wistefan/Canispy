pragma solidity ^0.5.0;

import "./ENS.sol";

contract ResolverBase {
    bytes4 private constant INTERFACE_META_ID = 0x01ffc9a7;

    function supportsInterface(bytes4 interfaceID) public pure returns(bool) {
        return interfaceID == INTERFACE_META_ID;
    }

    function isAuthorised(bytes32 node) internal view returns(bool);
    function _ens() internal view returns(ENS);

    modifier authorised(bytes32 node) {
        require(isAuthorised(node), "Caller is NOT authorised");
        _;
    }

    function bytesToAddress(bytes memory b) internal pure returns(address payable a) {
        require(b.length == 20);
        assembly {
            a := div(mload(add(b, 32)), exp(256, 12))
        }
    }

    function addressToBytes(address a) internal pure returns(bytes memory b) {
        b = new bytes(20);
        assembly {
            mstore(add(b, 32), mul(a, exp(256, 12)))
        }
    }
    
    function hash(string memory data) public pure returns(bytes32) {
        return keccak256(bytes(data));
    }

}
