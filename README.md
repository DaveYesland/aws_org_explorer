# AWS_ORG_MAPPER

This tool uses sso-oidc to authenticate to the AWS organization. Once authenticated the tool will attempt to enumerate all users and roles in the organization and map their trust relations. 

The graph can be explored using Neo4j desktop or web client. Below you can find some sample queries that can help extract useful information from the graph. 

Using this tool users can discover how role trusts are delegated in the organization and can help identify improve account isolation within the organization. For example, if there exists a role assumption path between two accounts the graph will be able to identify which roles and users are used to connect two accounts. 

![](./imgs/graph.png)

## Requirements 

* Neo4j
* boto3
* AWS SSO Account 
* py2neo

## How to Use

1. Install the Python3 requirements with `pip3 install -r requirements.txt`

2. Install Neo4j and add the connection details to `config.py`. 

3. Configure the SSO organization URL in `config.py`.

4. Run the tool with `python3 mapper.py`

If there is no `token` file stored in the directory the SSO auth flow will start. The instructions and device link will be printed to the console. After auth, the SSO token will be saved to `./token`. If you wish to run the tool on a new org make sure to delete the old `./token` file. 

The tool will attempt to use the first valid role associated with the SSO account. If there is access denied the tool will move the next available role within the account.

Once completed the graph is generated in Neo4j. Using the sample queries below or designed your own by referencing the structure in `## Graph Structure` you can begin to extract information about the organization.

### Notes

Does not currently support SAML Providers or SAML conditions. 

I am currently not planning on implementing an interface for this tool as it serves more as an import tool for neo4j. I will be continuing to implement a better interface for the CLI to give the user more control over the execution. 

# Example Queries 

* List all Accounts 

  `MATCH (a:Account) RETURN A`

* List all Roles

  `MATCH (r:Role) RETURN R`

* List all users

  `MATCH (u:User) RETURN u`

* Count number of cross-account relations 

  `MATCH p=(A:Account)-[:OWNS]->(x)-[:ASSUMES]->(y)<-[:OWNS]-(B:Account) RETURN COUNT(p)`

* Find all paths between account A and account B

  `MATCH p=(A:Account {accountId: "111111111"})-[:OWNS]->(x)-[:ASSUMES]->(y)<-[:OWNS]-(B:Account {accountId: "222222222"}) RETURN p`

* Find all routes from account A to any account 

  `MATCH p=(A:Account {accountId: "111111111"})-[:OWNS]->(x)-[:ASSUMES]->(y)<-[:OWNS]-(B:Account) RETURN p`

* Find all roles that trust ":root" of an account. 

  `MATCH p=(a:Account)-[:ASSUMES]->(:Role) RETURN p`

* Find all roles assumed by a specific service.

  `MATCH p=(:Service {Service: "lambda"})-[:ASSUMES]->(r:Role) WHERE r.accountID = "11111111111" RETURN p`

## Graph Structure

### Nodes and Attributes 


* Role
  - Arn
  - RoleId
  - RoleName
  - accountId

* Account 
  - accountId
  - accountName
  - emailAddress
* User
  - Arn
  - UserName
  - accountId
* Service
    - Service (lambda.amazonaws.com)


### Node Relations

* Account -[OWNS]->(Role/User)
* Account -[ASSUMES]-> (Role)
* Role -[ASSUMES]-> (Role)
* User -[ASSUMES]-> (Role)
* Service -[ASSUMES]-> (Role)



### Acknowledgment 

Thanks to Christophe Tafani-Dereeper for the sso device auth code. Their code can be found here. 

https://github.com/christophetd/aws-sso-device-code-authentication
