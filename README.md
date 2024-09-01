# APP RPT DNS Server
Python based DNS server supporting APP RPT Portals

This DNS server listens to a Kafka topic loading into memory any DNS entries sent. 

When a DNS request comes in, the DNS details are pulled from an In Memory TTL Cache and returned to the requester. 

This is still a work in process. 
