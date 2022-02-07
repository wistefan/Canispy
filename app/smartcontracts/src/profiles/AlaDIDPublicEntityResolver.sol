pragma solidity ^0.5.0;

import "../ENS.sol";
import "../ResolverBase.sol";

// This is a special "trusted attesting" resolver, in the sense that some record info associated
// to a node can not be set by the owner of the node, but it has to be set by the
// owner of the parent node. In other words, the parent node "attests" that the information associated
// to a given node is correct (under the responsibility of the parent node owner).
// It acts as an extension to the assignment of a name to a node (setSubnodeOwner), which can only be
// made by the parent node and under its responsibility.
// This means that anyone resolving the info from the node name knows that the info has been verified
// by the owner of the parent node. This is extremely useful in many real-world environments where
// Trusted Entities are required to attest some other entities.
// In addition to the trusted info, there is "normal" information that can be set by the owner of the node.
//
// In particular:
// Attested info by the parent: DID, name and active
// Self-managed info: DIDDocument (the parent can set initially that info if desired, but it can be changed later)
contract AlaDIDPublicEntityResolver is ResolverBase {

    // The EntityData includes:
    // DID The DID of the entity.
    // name The short name assigned to the entity.
    // DIDDocument The associated DIDDocument in JSON-LD format.
    // active A flag to allow pausing the entity.
    struct EntityData {
        bytes32 DIDHash;
        string domain_name;
        string DIDDocument;
        bool active;
    }

    // The main registry of entities
    // node => EntityData record
    mapping(bytes32 => EntityData) entities;

    // Fast resolution of DIDs
    // DID => node
    mapping(bytes32 => bytes32) nodes;

    // Reverse resolution of addresses to nodes, without an additional smart contract
    // address => node
    mapping(address => bytes32) nodes_from_address;

    // With the above structures, it is efficient to do the following:
    // - From a DID, get the DID Document (W3C DID Resolution)
    // - From an address, get the node and then the DID and DID Document
    //      This allows the usage of a standard address in any place, but efficienttly get the DID,
    //      if there is one associated.
    //      For companies and other public entities in the Alastria ecosystem, this should always be the case.
    // - From a DID or address, get the domain name assigned in ENS.
    //      This assumes that the trusted entity registering the DID uses the domain name that is associated,
    //      via the name_hash algorithm, to the node and label parameters.

    event AlaDIDDocumentChanged(bytes32 indexed node, string document);

    // We specify both the node and the subnode ("label"), the caller should be the owner of the parent node.
    // This is in contrast to "normal" resolvers, where only the target node is specified.
    function setAlaDIDPublicEntity(
        bytes32 node,
        bytes32 label,
        bytes32 _DIDHash,
        string calldata _domain_name,
        string calldata _DIDDocument,
        bool _active,
        address _owner
        ) external authorised(node) {

        // Check for lengths of strings
        require(bytes(_domain_name).length < 100, "Domain name too big");
        require(bytes(_DIDDocument).length < 3000, "DID Document too big");

        // Calculate the namehash of the subnode
        bytes32 subnode = keccak256(abi.encodePacked(node, label));

        // Assign ownership of the name to the specified address, via the ENS smart contract
        _ens().setSubnodeOwner(node, label, _owner);

        // Set the essential entity information for the subnode, that the subnode owner can not modify
        entities[subnode] = EntityData(
            _DIDHash,
            _domain_name,
            _DIDDocument,
            _active
        );

        // Update the list of DIDs, for easy resolution later
        nodes[_DIDHash] = subnode;

        nodes_from_address[_owner] = subnode;
 
    }

    /**
     * Returns the entity data associated with an ENS node.
     * @param node The ENS node to query.
     * @return The associated entity data.
     */
    function AlaDIDPublicEntity(bytes32 node) external view returns (
        bytes32 _DIDHash,
        string memory _domain_name,
        string memory _DIDDocument,
        bool _active
        ) {

        return (
            entities[node].DIDHash,
            entities[node].domain_name,
            entities[node].DIDDocument,
            entities[node].active
        );
    }

    function nodeFromDID(bytes32 _DIDHash) external view returns (bytes32 _node) {
        // Check for lengths of strings
        return nodes[_DIDHash];
    }

    function addressFromDID(bytes32 _DIDHash) external view returns (address _owner) {
        // Check for lengths of strings
        bytes32 node = nodes[_DIDHash];
        return _ens().owner(node);
    }


    /**
     * Sets the AlaDIDDocument associated with the ENS node that has the given DID.
     * May only be called by the owner of that node in the ENS registry.
     * @param _DIDHash The hash of the DID to update.
     * @param _DIDDocument The document to set.
     */
    function setAlaDIDDocument(bytes32 _DIDHash, string calldata _DIDDocument) external {
        // Check for lengths of strings
        require(bytes(_DIDDocument).length < 2000, "DID Document too big");

        // Get the associated node (if any)
        bytes32 node = nodes[_DIDHash];

        // The caller must be the owner of the node
        require(isAuthorised(node), "Caller is NOT authorised");

        // Set the document field in EntityData
        entities[node].DIDDocument = _DIDDocument;
        emit AlaDIDDocumentChanged(node, _DIDDocument);
    }


}
