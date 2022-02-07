// SPDX-License-Identifier:  	Apache-2.0
pragma solidity >=0.4.22 <0.7.0;


// This is a contract managing Self-declarations
contract PublicSelfDeclarations {

    // Maximum number of participant
    uint256 constant maxParticipants = 10;

    // The struct for storing the data of a Self-declaration
    struct PublicSelfDeclaration {
        bool exists;
        uint256 index;
        string declarationHash;
        string offchainURI;
        string payload;
        address declarationOwner;
        uint256 numParticipants;
        mapping (uint => address) participants;
    }

    // The total number of declarations registered
    uint256 numberDeclarations;

    // The mappings to ensure that a notary can notarize a hash only once
    // documentHash => PublicSelfDeclaration
    mapping(string => PublicSelfDeclaration) private attestationRegistry;

    // The list of all attestations
    mapping(uint256 => string) private attestationList;


    // Register a Self-declaration
    // In this implementation, ALL users can register self-declarations,
    // and no checks are done on the number of participants in a single declaration
    // Additionally, no checks are currently done on the documenthash input parameter.
    // Anyway, if the documenthash is not a real hash, no harm is done to the system, except
    // that there maybe some "garbage" in the data.
    //
    // Input: declarationHash, offchainURI, payload
    function selfDeclare(
        string memory declarationHash,
        string memory offchainURI,
        string memory payload
    ) public {
        // Anybody can register a Self-declaration. The caller will assume the role SELF_DECLARATION_OWNER for that declaration

        // Check if this is the first registration of the declaration, by using the hash
        if (!attestationRegistry[declarationHash].exists) {

            // This is a new declaration
            attestationRegistry[declarationHash] = PublicSelfDeclaration(
                true,
                numberDeclarations,
                declarationHash,
                offchainURI,
                payload,
                msg.sender,
                1
            );

            attestationRegistry[declarationHash].participants[0] = msg.sender;

            attestationList[numberDeclarations] = declarationHash;
            numberDeclarations++;

        } else {

            // We are declaring against an existent declaration

            // First we have to check if the caller has already declared
            for (uint i = 0; i < attestationRegistry[declarationHash].numParticipants; i++) {
                if (attestationRegistry[declarationHash].participants[i] == msg.sender) {
                    return;
                }
            }

            // Check if we exceeded the number of participants
            uint256 numParticipants = attestationRegistry[declarationHash].numParticipants;
            require(numParticipants < maxParticipants, "Number of participants exceeded");

            // Add the new participant and update the count
            attestationRegistry[declarationHash].participants[numParticipants] = msg.sender;
            attestationRegistry[declarationHash].numParticipants = numParticipants + 1;

        }
    }

    // Get declaration data (without participants, which have to be recovered apart)
    function getDeclaration(
        string memory declarationHash
    )
        public
        view
        returns (
            uint256 index,
            string memory offchainURI,
            string memory payload,
            address declarationOwner,
            uint256 numParticipants
        )
    {
        // Check that the declaratin exists
        require(
            attestationRegistry[declarationHash].exists,
            "Declaration does not exist"
        );

        // Get the attestation struct
        PublicSelfDeclaration storage att = attestationRegistry[declarationHash];

        // Return the relevant fields of the attestation
        return (att.index, att.offchainURI, att.payload, att.declarationOwner, att.numParticipants);

    }


    // Get the participant at a given index
    function getParticipantByIndex(
        string memory declarationHash,
        uint256 participantIndex
    )
        public
        view
        returns (
            address participant
        )
    {
        // Check that the declaratin exists
        require(attestationRegistry[declarationHash].exists, "Declaration does not exist");

        // Check validity of participantIndex
        require(attestationRegistry[declarationHash].numParticipants > participantIndex, "ParticipantIndex too big");

        // Get the attestation struct
        PublicSelfDeclaration storage att = attestationRegistry[declarationHash];

        // Return the relevant fields of the attestation
        return att.participants[participantIndex];

    }


    // Get the total number of declarations
    function numberOfDeclarations()
        public
        view
        returns (uint256 numDeclarations)
    {
        return numberDeclarations;
    }

}