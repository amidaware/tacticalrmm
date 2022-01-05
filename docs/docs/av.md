## Bitdefender Gravityzone

Admin URL: <https://cloud.gravityzone.bitdefender.com/>

To exclude URLs: Policies > {policy name} > Network Protection > Content Control > Settings > Exclusions

![Web Exclusions](images/avbitdefender_gravityzone_exclusions0.png)

![Web Exclusions](images/avbitdefender_gravityzone_exclusions1.png)

![Web Exclusions](images/avbitdefender_gravityzone_exclusions2.png)

## Webroot

Admin URL:

![Web Exclusions](images/avwebroot.png)

![Web Exclusions](images/avwebroot5.png)

![Web Exclusions](images/avwebroot4.png)

![Web Exclusions](images/avwebroot3.png)

![Web Exclusions](images/avwebroot2.png)

![Web Exclusions](images/avwebroot1.png)

## Sophos

### Sophos Central Admin

Go To Global Settings >> General >> Global Exclusions >> Add Exclusion

![Agent Exclusions](images/sophoscascreen1.png)

![Agent Exclusions](images/sophoscascreen2.png)

![Agent Exclusions](images/sophoscascreen3.png)

![Agent Exclusions](images/sophoscascreen4.png)

![Agent Exclusions](images/sophoscascreen5.png)

![Agent Exclusions](images/sophoscascreen6.png)

![Agent Exclusions](images/sophoscascreen7.png)

### Sophos XG Firewall

![Agent Exclusions](images/sophoscascreen1.png)

Log into Sophos Central Admin

Admin URL: <https://cloud.sophos.com/>

Log into the Sophos XG Firewall

Go To System >> Hosts and services >> FQDN Host Group and create a new group

![FW Exclusions](images/sophosxgscreen1.png)

Go To System >> Hosts and services >> FQDN Host

Create the following 3 hosts and add each to your FQDN host group.

- api.yourdomain.com
- mesh.yourdomain.com
- rmm.yourdomain.com (Optional if you want your client to have GUI access to Tactical RMM)

![FW Exclusions](images/sophosxgscreen2.png)

![FW Exclusions](images/sophosxgscreen3.png)

Go To Hosts and services >> Services and create the following services

- Name: Tactical-Service-4222
    - Protocol: TCP
    - Source port: 1:65535
    - Destination port: 4222
- Name: Tactical-Service-443
    - Protocol: TCP
    - Source port: 1:65535
    - Destination port: 443

![FW Exclusions](images/sophosxgscreen4.png)

![FW Exclusions](images/sophosxgscreen5.png)

Go To Hosts and services >> Service group and create the following service group

![FW Exclusions](images/sophosxgscreen6.png)

Go To Protect >> Rules and policies and add a firewall rule

- Rule name: Tactical Rule
- Rule position: Top
- Source zones: LAN
- Source networks: ANY
- Destination zones: WAN
- Destination networks: Your FQDN Host Group
- Services: Tactical Services

![FW Exclusions](images/sophosxgscreen7.png)

![FW Exclusions](images/sophosxgscreen8.png)

Optionally select Log Firewall Traffic checkbox for troubleshooting.
