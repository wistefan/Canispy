pragma solidity ^0.5.0;

import "../ENS.sol";
import "../ResolverBase.sol";

contract PublicEntityResolver {
    function addressFromDID(bytes32 _DIDHash) external view returns (address _owner);
}

// This is a contract managing Self-declarations
contract AlaPublicCredentialResolver is ResolverBase {

    // Maximum number of participants
    uint constant maxParticipants = 10;

    // The struct for participant data
    struct Participant {
        bytes32 DIDHash;
        bool signed;
    }

    // The struct for storing the data of a Public Credential
    struct PublicCredential {
        bool exists;
        bytes credentialHash;
        Participant[] participants;
    }

    // node => credentialHash => PublicCredential
    mapping(bytes32 => PublicCredential) credentials;

    // Create the credential, with the possibility to specify up to 5 initial participants
    function setCredential(
        bytes32 node,
        bytes calldata credentialHash,
        bytes32 part1DIDhash,
        bytes32 part2DIDhash,
        bytes32 part3DIDhash,
        bytes32 part4DIDhash,
        bytes32 part5DIDhash
    ) external {

        // The caller must be the owner (or authorised), to be able to create a Public Credential associated to that node.
        require(isAuthorised(node), "setCredential, caller is NOT authorised");

        // Check for lengths of bytes and strings
        require(credentialHash.length < 100, "Participant1DID too big");

        PublicCredential storage cred = credentials[node];
        cred.exists = true;
        cred.credentialHash = credentialHash;

        // Erase the participants field, if there was something
        cred.participants.length = 0;

        // Add each participant to the participants list
        bytes32 didh;

        didh = part1DIDhash;
        if (didh != 0) {
            cred.participants.push(Participant({
                DIDHash: didh,
                signed: false
            }));
        }

        didh = part2DIDhash;
        if (didh != 0) {
            cred.participants.push(Participant({
                DIDHash: didh,
                signed: false
            }));
        }

        didh = part3DIDhash;
        if (didh != 0) {
            cred.participants.push(Participant({
                DIDHash: didh,
                signed: false
            }));
        }

        didh = part4DIDhash;
        if (didh != 0) {
            cred.participants.push(Participant({
                DIDHash: didh,
                signed: false
            }));
        }

        didh = part5DIDhash;
        if (didh != 0) {
            cred.participants.push(Participant({
                DIDHash: didh,
                signed: false
            }));
        }

        return;
    
    }

        
    function addParticipant(
        bytes32 node,
        bytes32 partDIDHash
    ) external {

        // The caller must be the owner (or authorised), to be able to create a Public Credential associated to that node.
        require(isAuthorised(node), "addParticipant, caller is NOT authorised");
 
        PublicCredential storage cred = credentials[node];
        require(cred.exists, "addParticipant, credential does not exist");

        require(cred.participants.length < 10, "addParticipant, too many participants");

        if (partDIDHash != 0) {
            cred.participants.push(Participant({
                DIDHash: partDIDHash,
                signed: false
            }));
        }
    }


    function confirmCredential(
        bytes32 node,
        bytes32 partDIDHash
    ) external {

        PublicCredential storage cred = credentials[node];
        require(cred.exists, "confirmCredential, credential does not exist");

        // First, check if the received DID is one of the participants in the credential
        bool isParticipant = false;
        uint i;
        for (i = 0; i < cred.participants.length; i++) {
            if (cred.participants[i].DIDHash == partDIDHash) {
                isParticipant = true;
                break;
            }
        }

        // Throw if the DID is not a participant
        require(isParticipant == true, "confirmCredential, is not participant");

        // Cast our contract address to a PublicEntity resolver, to be able to call its API
        PublicEntityResolver res = PublicEntityResolver(address(this));

        // Get the address controlling the DID associated to the hash that we received
        address _owner = res.addressFromDID(partDIDHash);

        // Check if the caller is the owner of the DID
        require(_owner == msg.sender, "confirmCredential, caller does not control DID");

        // Mark the participant as signed
        cred.participants[i].signed = true;

        return;
    }


    function credential(bytes32 node) external view returns (bytes memory credentialHash, uint numParticipants) {
        PublicCredential storage cred = credentials[node];
        require(cred.exists, "credential, credential does not exist");

        return (cred.credentialHash, cred.participants.length);
    }

    function credentialParticipant(bytes32 node, uint index) external view
                returns (bytes32 didHash, bool signed) {

        PublicCredential storage cred = credentials[node];
        require(cred.exists, "credentialParticipant, credential does not exist");
        require(cred.participants.length > index, "credentialParticipant, index out of range");

        return (cred.participants[index].DIDHash, cred.participants[index].signed);
    }



}