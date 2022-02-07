Tolar node is standalone node binary which connects to Tolar HashNET network. It exposes all available functionality to client via gRPC API and also has address and key managment functionality. 

Files contained:
tolar_node_bin - executable binary for Tolar node
gRPC_api_documentation.pdf - Documentation with examples for available API
config.json - Configuration file containing seed nodes IP for connecting to network, key store configuration and client end point configuration
proto/ - Directory including .proto files for gRPC API

Starting the node
=================

Before starting make sure to set correct directory for your keystore! 
In config.json there are properties:
'keys_file_path'
'secrets_path'
which you need to set to locations where you want your keystore to be. Included examples are what would be probable place that someone with username 'tolar' would set them to, but any location that you have write access to should do. Usually, you'll just replace tolar user with your username, for example:
    "keys_file_path": "/home/tolar/.tolar/keystore/keys.info",
    "secrets_path": "/home/tolar/.tolar/keystore/keys"
 would become:
    "keys_file_path": "/home/john/.tolar/keystore/keys.info",
    "secrets_path": "/home/john/.tolar/keystore/keys"

 If you move your keystore directory manually, you'll need to update it in config.json if you want to preserve your addresses and private keys. 

 Once you've setup your config, you can start node binary and provide it path to configuration file. You can have multiple networks, or keystores in multiple configuration files, so when you want to switch you can just start binary with wanted config.json.
 For example:

 ./tolar_node_bin --config_path=/home/john/config.json