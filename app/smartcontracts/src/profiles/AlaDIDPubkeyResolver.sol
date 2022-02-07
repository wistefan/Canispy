pragma solidity ^0.5.0;

import "../ResolverBase.sol";

contract AlaDIDPubkeyResolver is ResolverBase {
    bytes4 constant private TEXT_INTERFACE_ID = 0x59d1d43c;

    // The status of a keyID. A deleted keyID is permanently deleted
    enum Status {NonExistent, Valid, RevokedBySubject, DeletedBySubject} // NonExistent == 0
    struct DIDPublicKeyValue {
        Status status; // Deleted keys shouldnt be used, not even to check previous signatures.
        uint startDate;
        uint endDate;
        string keyValue;
    }

    event AlaDIDPubkeyAdded(bytes32 indexed node, string indexed indexedKey, string keyID);
    event AlaDIDPubkeyRevoked(bytes32 indexed node, string indexed indexedKey, string keyID);
    event AlaDIDPubkeyDeleted(bytes32 indexed node, string indexed indexedKey, string keyID);

    // node -> KeyID -> array of DIDPublicKeyValue structures (to keep the history of the keys with same KeyID)
    mapping(bytes32=>mapping(string=>DIDPublicKeyValue[])) AlaDIDPubkeys;

    /**
     * Adds a public key associated with an ENS node and keyID.
     * May only be called by the owner of that node in the ENS registry.
     * @param node The node to update.
     * @param keyID The keyID to set.
     * @param keyValue The key value to set. Should be in JSON Web Key format (JWK)
     */
    function addPublicKey(bytes32 node, string calldata keyID, string calldata keyValue) external authorised(node) {

        // If there is already a key for this node and keyID, set the end date and mark it as revoked
        uint numKeys = AlaDIDPubkeys[node][keyID].length;
        if (numKeys > 0) {
            AlaDIDPubkeys[node][keyID][numKeys-1].endDate = now;
            AlaDIDPubkeys[node][keyID][numKeys-1].status = Status.RevokedBySubject;
        }

        // Add a new DIDPublicKeyValue element to the array of keys identified by keyID for this node
        AlaDIDPubkeys[node][keyID].push(
            DIDPublicKeyValue(
                Status.Valid,
                now,
                0,
                keyValue
            )
        );
        emit AlaDIDPubkeyAdded(node, keyID, keyID);
    }

    /**
     * Returns the public key data associated with an ENS node and keyID. The latest key (if there are more than one) is returned.
     * @param node The ENS node to query.
     * @param keyID The id of the key to query.
     * @return The associated public key value.
     */
    function publicKey(bytes32 node, string calldata keyID) external view
            returns (Status status, uint startDate, uint endDate, string memory keyValue, uint keyIndex) {

        // Return nil values if there are no keys (we do not want to throw and error)
        uint numKeys = AlaDIDPubkeys[node][keyID].length;
        if (numKeys == 0) {
            return (Status.NonExistent, 0, 0, "", 0);
        }

        DIDPublicKeyValue storage pubKey = AlaDIDPubkeys[node][keyID][numKeys-1];

        return (pubKey.status, pubKey.startDate, pubKey.endDate, pubKey.keyValue, numKeys-1);
    }

    /**
     * Returns the public key data associated with an ENS node and keyID, for the given index.
     * @param node The ENS node to query.
     * @param keyID The id of the key to query.
     * @param index The index in the array of keys for the given keyID.
     * @return The associated key value.
     */
    function publicKeyAtIndex(bytes32 node, string calldata keyID, uint index) external view
            returns (Status status, uint startDate, uint endDate, string memory keyValue) {

        // Get the size of the array holding the DIDPublicKeyValue structures
        uint numKeys = AlaDIDPubkeys[node][keyID].length;

        // Return nil values if there are no keys or index is out of bounds (we do not want to throw and error)
        if (numKeys == 0 || index >= numKeys) {
            return (Status.NonExistent, 0, 0, "");
        }

        // Return the public key data for the specified index
        DIDPublicKeyValue storage pubKey = AlaDIDPubkeys[node][keyID][index];

        return (pubKey.status, pubKey.startDate, pubKey.endDate, pubKey.keyValue);
    }


    /**
     * Revokes a public key associated with an ENS node, keyID and index.
     * May only be called by the owner of that node in the ENS registry.
     * @param node The node to update.
     * @param keyID The keyID to set.
     * @param index The index in the array of keys for the given keyID.
     * @return The associated key value.
     */
    function revokePublicKey(bytes32 node, string calldata keyID, uint index) external authorised(node) {

        // Get the size of the array holding the DIDPublicKeyValue structures
        uint numKeys = AlaDIDPubkeys[node][keyID].length;

        // Return if there are no keys or index is out of bounds (we do not want to throw and error)
        if (numKeys == 0 || index >= numKeys) {
            return;
        }

        // Do nothing if the public key was deleted in the past
        if (AlaDIDPubkeys[node][keyID][index].status == Status.DeletedBySubject) {
            return;
        }

        // Set the end date and mark it as revoked
        AlaDIDPubkeys[node][keyID][index].endDate = now;
        AlaDIDPubkeys[node][keyID][index].status = Status.RevokedBySubject;

        emit AlaDIDPubkeyRevoked(node, keyID, keyID);
    }

    /**
     * Deletes a public key associated with an ENS node, keyID and index.
     * May only be called by the owner of that node in the ENS registry.
     * @param node The node to update.
     * @param keyID The keyID to set.
     * @param index The index in the array of keys for the given keyID.
     * @return The associated key value.
     */
    function deletePublicKey(bytes32 node, string calldata keyID, uint index) external authorised(node) {

        // Get the size of the array holding the DIDPublicKeyValue structures
        uint numKeys = AlaDIDPubkeys[node][keyID].length;

        // Return if there are no keys or index is out of bounds (we do not want to throw and error)
        if (numKeys == 0 || index >= numKeys) {
            return;
        }

        // Set the end date and mark it as revoked
        AlaDIDPubkeys[node][keyID][index].endDate = now;
        AlaDIDPubkeys[node][keyID][index].status = Status.DeletedBySubject;

        emit AlaDIDPubkeyDeleted(node, keyID, keyID);
    }

    function supportsInterface(bytes4 interfaceID) public pure returns(bool) {
        return interfaceID == TEXT_INTERFACE_ID || super.supportsInterface(interfaceID);
    }
}
