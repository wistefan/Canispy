pragma solidity ^0.5.0;

import "../ResolverBase.sol";

contract AlaDIDDocumentResolver is ResolverBase {
    bytes4 constant private document_INTERFACE_ID = 0x691f3431;

    event AlaDIDDocumentChanged(bytes32 indexed node, string document);

    mapping(bytes32=>string) AlaDIDDocuments;

    /**
     * Sets the AlaDIDDocument associated with an ENS node, for reverse records.
     * May only be called by the owner of that node in the ENS registry.
     * @param node The node to update.
     * @param document The document to set.
     */
    function setAlaDIDDocument(bytes32 node, string calldata document) external authorised(node) {
        AlaDIDDocuments[node] = document;
        emit AlaDIDDocumentChanged(node, document);
    }

    /**
     * Returns the AlaDIDDocument associated with an ENS node, for reverse records.
     * @param node The ENS node to query.
     * @return The associated document.
     */
    function AlaDIDDocument(bytes32 node) external view returns (string memory) {
        return AlaDIDDocuments[node];
    }

    function supportsInterface(bytes4 interfaceID) public pure returns(bool) {
        return interfaceID == document_INTERFACE_ID || super.supportsInterface(interfaceID);
    }
}
