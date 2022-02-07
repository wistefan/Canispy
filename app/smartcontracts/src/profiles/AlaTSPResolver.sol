pragma solidity ^0.5.0;

import "../ENS.sol";
import "../ResolverBase.sol";

// This is a special "trusted attesting" resolver, in the sense that the record info associated
// to a node can not be set by the owner of the node, but it has to be set by the
// owner of the parent node. In other words, the parent node "attests" that the information associated
// to a given node is correct (under the responsibility of the parent node owner).
// It acts as an extension to the assignment of a name to a node (setSubnodeOwner), which can only be
// made by the parent node and under its responsibility.
// This means that anyone resolving the info from the node name knows that the info has been verified
// by the owner of the parent node. This is extremely useful in many real-world environments where
// Trusted Entities are required to attest some other entities.
contract AlaTSPResolver is ResolverBase {

    // The TSP Service data includes:
    // X509SKI The SubjectKeyIdentifier of the associated X509 certificate.
    // serviceName The service name as it appears in the official Trusted List.
    // X509Certificate The full x509 certificate in PEM format (except the begin and end text lines).
    // active A flag to allow pausing the service.
    struct TSPServiceData {
        string X509SKI;
        string serviceName;
        bytes X509Certificate;
        bool active;
    }

    // We store the URI of the entity, as it appears in the "classical" Trusted List. URI is unique.
    // We also store the org name as it appears in the X509 certificate
    // The flag "active" can be used to stop and resume the entity if needed
    struct TSPData {
        string URI;
        string org;
        bool active;
        TSPServiceData[] services;
    }

    // The main registry of TSPs
    // node => TSP data record
    mapping(bytes32 => TSPData) TSPs;

    // We specify both the node and the subnode ("label"), the caller should be the owner of the parent node.
    // This is in contrast to "normal" resolvers, where only the target node is specified.
    function setAlaTSP(
        bytes32 node,
        bytes32 label,
        string calldata URI,
        string calldata org,
        bool active
        ) external authorised(node) {

        // Calculate the namehash of the subnode
        bytes32 subnode = keccak256(abi.encodePacked(node, label));

        // Check that the subnode exists in ENS before atempting to set the info
        require(_ens().recordExists(subnode), "Subnode does not exist");

        // Set the attested entity information for the subnode
        // Even the subnode owner can not modify this information
        TSPData storage tsp = TSPs[subnode];
        tsp.URI = URI;
        tsp.org = org;
        tsp.active = active;
 
    }

    // We specify both the node and the subnode ("label"), the caller should be the owner of the parent node.
    // This is in contrast to "normal" resolvers, where only the target node is specified.
    function addAlaTSPService(
        bytes32 node,
        bytes32 label,
        string calldata X509SKI,
        string calldata serviceName,
        bytes calldata X509Certificate,
        bool active
        ) external authorised(node) {

        // Calculate the namehash of the subnode
        bytes32 subnode = keccak256(abi.encodePacked(node, label));

        // Check that the subnode TSP data is active before atempting to set the info
        require(TSPs[subnode].active, "Subnode does not have active TSP data");

        // Set the attested entity information for the subnode
        // Even the subnode owner can not modify this information
        TSPs[subnode].services.push(
            TSPServiceData(
                X509SKI,
                serviceName,
                X509Certificate,
                active
            )
        );

    }

    /**
     * Returns the entity data associated with an ENS node.
     * @param node The ENS node to query.
     * @return The associated entity data.
     */
    function AlaTSP(bytes32 node) external view returns (
            string memory URI,
            string memory org,
            bool active
        ) {

        // Check that the subnode TSP data is active before atempting to set the info
        require(TSPs[node].active, "Subnode does not have active TSP data");

//        return ("Perico", "Juan", TSPs[node].active);
        return (TSPs[node].URI, TSPs[node].org, TSPs[node].active);

    }

    /**
     * Returns the number of services provided by a given TSP.
     * @param node The ENS node to query.
     * @return The number of registered services, both active and inactive.
     */
    function AlaTSPNumberServices(bytes32 node) external view returns (uint) {
        return TSPs[node].services.length;
    }

    /**
     * Returns the TSP Service data at a given index for the specified TSP.
     * @param node The ENS node to query.
     * @return The associated entity data.
     */
    function AlaTSPService(bytes32 node, uint index) external view returns (
            string memory X509SKI,
            string memory serviceName,
            bytes memory X509Certificate,
            bool active
        ) {

        if (index < TSPs[node].services.length) {
            return (
                TSPs[node].services[index].X509SKI,
                TSPs[node].services[index].serviceName,
                TSPs[node].services[index].X509Certificate,
                TSPs[node].services[index].active
            );
        }

    }

}
