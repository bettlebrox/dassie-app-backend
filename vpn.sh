#!/bin/bash
echo "modifying vpn: ${1}"
if [[ "$1" == "stop" ]]; then
	aws ec2 describe-client-vpn-target-networks --client-vpn-endpoint-id cvpn-endpoint-0a86f846d33b6c34f --query 'ClientVpnTargetNetworks[*].AssociationId' | jq -rc '.[]' | while read association_id; do
		echo "disassociating association: ${association_id}"
		echo "aws ec2 disassociate-client-vpn-target-network --client-vpn-endpoint-id cvpn-endpoint-0a86f846d33b6c34f --association-id ${association_id}"
		aws ec2 disassociate-client-vpn-target-network --client-vpn-endpoint-id cvpn-endpoint-0a86f846d33b6c34f --association-id ${association_id} --debug
		aws ec2 describe-client-vpn-connections --client-vpn-endpoint-id cvpn-endpoint-0a86f846d33b6c34f --query "Connections[*].ConnectionId" --filters "Name=status,Values=active" | jq -rc '.[]' | while read connection_id; do
			aws ec2 terminate-client-vpn-connections --client-vpn-endpoint-id cvpn-endpoint-0a86f846d33b6c34f --connection-id ${connection_id}
		done
	done
elif [[ "$1" == "start" ]]; then
	aws ec2 associate-client-vpn-target-network --subnet-id subnet-08333ed8542ffa19f --client-vpn-endpoint-id cvpn-endpoint-0a86f846d33b6c34f
fi
