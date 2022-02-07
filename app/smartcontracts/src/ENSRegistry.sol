pragma solidity ^0.5.0;

import "./ENS.sol";

/**
 * The ENS registry contract.
 */
contract ENSRegistry is ENS {

    struct Record {
        address owner;
        address resolver;
        uint64 ttl;
        bytes32[] subnodes;
    }

    // Maps from node to its record
    mapping (bytes32 => Record) records;

    // The addresses that are authorised to operate as if they are the owners of the node
    mapping (address => mapping(address => bool)) operators;

    // Permits modifications only by the owner of the specified node,
    // or by the operators authorized by the owner
    modifier authorised(bytes32 node) {
        address owner = records[node].owner;
        require(owner == msg.sender || operators[owner][msg.sender], "Caller is NOT authorised");
        _;
    }

    /**
     * @dev Constructs a new ENS registrar.
     */
    constructor() public {
        records[0x0].owner = msg.sender;
    }

    /**
     * @dev Sets the record for a node.
     * @param node The node to update.
     * @param _owner The address of the new owner.
     * @param _resolver The address of the resolver.
     * @param _ttl The TTL in seconds.
     */
    function setRecord(bytes32 node, address _owner, address _resolver, uint64 _ttl) external {

        address owner = records[node].owner;
        require(owner == msg.sender || operators[owner][msg.sender], "setRecord: Caller is NOT authorised");

        setOwner(node, _owner);
        _setResolverAndTTL(node, _resolver, _ttl);
    }

    /**
     * @dev Sets the record for a subnode.
     * @param node The parent node.
     * @param label The hash of the label specifying the subnode.
     * @param _owner The address of the new owner.
     * @param _resolver The address of the resolver.
     * @param _ttl The TTL in seconds.
     */
    function setSubnodeRecord(bytes32 node, bytes32 label, address _owner, address _resolver, uint64 _ttl) external {

        address owner = records[node].owner;
        require(owner == msg.sender || operators[owner][msg.sender], "setSubnodeRecord: Caller is NOT authorised");

        bytes32 subnode = setSubnodeOwner(node, label, _owner);
        _setResolverAndTTL(subnode, _resolver, _ttl);

    }

    /**
     * @dev Transfers ownership of a node to a new address. The caller has to be the owner or be authorised.
     * @param node The node to transfer ownership of.
     * @param _owner The address of the new owner.
     */
    function setOwner(bytes32 node, address _owner) public {
        address owner = records[node].owner;
        require(owner == msg.sender || operators[owner][msg.sender], "setOwner: Caller is NOT authorised");

        _setOwner(node, _owner);
        emit Transfer(node, _owner);
    }

    /**
     * @dev Transfers ownership of a subnode keccak256(node, label) to a new address. May only be called by the owner of the parent node.
     * @param node The parent node.
     * @param label The hash of the label specifying the subnode.
     * @param _owner The address of the new owner.
     */
    function setSubnodeOwner(bytes32 node, bytes32 label, address _owner) public returns(bytes32) {

        address owner = records[node].owner;
        require(owner == msg.sender || operators[owner][msg.sender], "setSubnodeOwner: Caller is NOT authorised");

        bytes32 subnode = keccak256(abi.encodePacked(node, label));
        _setOwner(subnode, _owner);

        // Only add the subnode to the list if it is not already in the list
        bool notFound = true;
        uint numSubnodes = records[node].subnodes.length;
        for (uint i=0; i<numSubnodes; i++) {
            if (records[node].subnodes[i] == subnode) {
                notFound = false;
                break;
            }
        }
        if (notFound) {
            records[node].subnodes.push(subnode);
        }
        emit NewOwner(node, label, _owner);
        return subnode;
    }

    /**
     * @dev Sets the resolver address for the specified node.
     * @param node The node to update.
     * @param _resolver The address of the resolver.
     */
    function setResolver(bytes32 node, address _resolver) public {

        address owner = records[node].owner;
        require(owner == msg.sender || operators[owner][msg.sender], "setResolver: Caller is NOT authorised");

        emit NewResolver(node, _resolver);
        records[node].resolver = _resolver;
    }

    /**
     * @dev Sets the TTL for the specified node.
     * @param node The node to update.
     * @param _ttl The TTL in seconds.
     */
    function setTTL(bytes32 node, uint64 _ttl) public {

        address owner = records[node].owner;
        require(owner == msg.sender || operators[owner][msg.sender], "setTTL: Caller is NOT authorised");

        emit NewTTL(node, _ttl);
        records[node].ttl = _ttl;
    }

    /**
     * @dev Enable or disable approval for a third party ("operator") to manage
     *  all of `msg.sender`'s ENS records. Emits the ApprovalForAll event.
     * @param operator Address to add to the set of authorized operators.
     * @param approved True if the operator is approved, false to revoke approval.
     */
    function setApprovalForAll(address operator, bool approved) external {
        operators[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    /**
     * @dev Returns the address that owns the specified node.
     * @param node The specified node.
     * @return address of the owner.
     */
    function owner(bytes32 node) public view returns (address) {
        address addr = records[node].owner;
        return addr;
    }

    /**
     * @dev Returns the number of subnodes of the specified subnode.
     * @param node The specified node.
     * @return number of subnodes. Zero also if the node does not exist.
     */
    function numberSubnodes(bytes32 node) public view returns (uint) {
        return records[node].subnodes.length;
    }

    /**
     * @dev Returns the subnode at index of the given node.
     * @param node The specified node.
     * @param index The specified index in the subnodes array.
     * @return address of the owner.
     */
    function subnode(bytes32 node, uint64 index) public view returns (bytes32) {
        if (index >= records[node].subnodes.length) {
            return 0;
        }
        return records[node].subnodes[index];
    }

    /**
     * @dev Returns the address of the resolver for the specified node.
     * @param node The specified node.
     * @return address of the resolver.
     */
    function resolver(bytes32 node) public view returns (address) {
        return records[node].resolver;
    }

    /**
     * @dev Returns the TTL of a node, and any records associated with it.
     * @param node The specified node.
     * @return ttl of the node.
     */
    function ttl(bytes32 node) public view returns (uint64) {
        return records[node].ttl;
    }

    /**
     * @dev Returns whether a record has been imported to the registry.
     * @param node The specified node.
     * @return Bool if record exists
     */
    function recordExists(bytes32 node) public view returns (bool) {
        return records[node].owner != address(0x0);
    }

    /**
     * @dev Query if an address is an authorized operator for another address.
     * @param _owner The address that owns the records.
     * @param operator The address that acts on behalf of the owner.
     * @return True if `operator` is an approved operator for `owner`, false otherwise.
     */
    function isApprovedForAll(address _owner, address operator) external view returns (bool) {
        return operators[_owner][operator];
    }

    function _setOwner(bytes32 node, address _owner) internal {
        records[node].owner = _owner;
    }

    function _setResolverAndTTL(bytes32 node, address _resolver, uint64 _ttl) internal {
        if(_resolver != records[node].resolver) {
            records[node].resolver = _resolver;
            emit NewResolver(node, _resolver);
        }

        if(_ttl != records[node].ttl) {
            records[node].ttl = _ttl;
            emit NewTTL(node, _ttl);
        }
    }
}
