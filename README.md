# Server Decommission with Ansible and Jira

Based on Jira ticket with special status.

Note. As a result, the technical staff should know from the Jira ticket comment which steps were successful or not, whether it is necessary to do a PR with Puppet configuration changes.

Ansible workflow:

1. Find Jira issue and filter hosts inventory
    * Find jira issue with status *Ready for Decomm*
    * Get host names from the ticket(s)
    * Create report as Jira ticket comment
    * Update Jira ticker status *Decom In Progress*

2. Shutdown host
    * Ping host
    * Shutdown if available

3. Remove Puppet Config
    * Revoke Certificate from Puppet server
    * Remove host from PuppetDB

4. Remove DNS records
    * Resolve host ip address
    * Remove A DNS records
    * Remove PTR DNS records

5. Reclaim/Remove IP Space
    * Check device name (fqdn or not)
    * Check if the device is present in **Device42**
    * Release device ips from **Device42**

6. Puppet Cleanup
    * Clone Puppet configs repo, checkout branch, delete host config folder, commit and push changes

7. Disable monitoring
    * Remove host from Sensu monitoring

8. Infrastructure Cleanup
    * Update host info in **Device42** system
    * Shutdown network interface(s) on switch(es)
    * Remove port(s) description.

9. Inventory Cleanup
    * Change device lifecycle to DECOMMISSIONED in **Device42**
    * Update device tags in **Device42**

10. Report
    * Create report as handler in Ansible logs

11. Jira comment
    * Create report as handler in Jira ticket
