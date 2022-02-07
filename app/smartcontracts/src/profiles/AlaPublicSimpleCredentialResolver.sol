pragma solidity ^0.5.0;

import "../ResolverBase.sol";

contract AlaPublicCredentialResolver is ResolverBase {
    bytes4 constant private AlaPublicCredential_INTERFACE_ID = 0x59d1d43c;

    event AlaPublicCredentialChanged(bytes32 indexed node, string indexed indexedKey, string key);

    mapping(bytes32=>mapping(string=>string)) AlaPublicCredentials;

    /**
     * Sets the AlaPublicCredential data associated with an ENS node and key.
     * May only be called by the owner of that node in the ENS registry.
     * @param node The node to update.
     * @param key The key to set.
     * @param value The AlaPublicCredential data value to set.
     */
    function setAlaPublicCredential(bytes32 node, string calldata key, string calldata value) external authorised(node) {
        AlaPublicCredentials[node][key] = value;
        emit AlaPublicCredentialChanged(node, key, key);
    }

    /**
     * Returns the AlaPublicCredential data associated with an ENS node and key.
     * @param node The ENS node to query.
     * @param key The AlaPublicCredential data key to query.
     * @return The associated AlaPublicCredential data.
     */
    function AlaPublicCredential(bytes32 node, string calldata key) external view returns (string memory) {
        return AlaPublicCredentials[node][key];
    }

    function supportsInterface(bytes4 interfaceID) public pure returns(bool) {
        return interfaceID == AlaPublicCredential_INTERFACE_ID || super.supportsInterface(interfaceID);
    }
}
