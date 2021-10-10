# BitDefender GravityZone Deployment

## How to Deploy BitDefender GravityZone

From the UI go to **Settings > Global Settings > CUSTOM FIELDS > Clients**

Add a Custom Field</br>

First: </br>
**Target** = `CLIENTS`</br>
**Name** = `bdurl`</br>
**Field Type** = `Text`</br>

![Service Name](images/3rdparty_bdg_RmmCustField.png)

Log into your GravityZone and on the left hand side, select "Packages" under "Network".

![Service Name](images/3rdparty_bdg_Packages.png)

Select the client you are working with and click "Send Download Links" at the top. </br>

![Service Name](images/3rdparty_bdg_DownloadLink.png)

Copy the appropriate download link

![Service Name](images/3rdparty_bdg_LinkCopy.png)

Paste download link into the `bdurl` when you right click your target clients name in the RMM.

![Service Name](images/3rdparty_bdg_CustFieldLink.png)

Right click the Agent you want to deploy to and **Run Script**. Select **BitDefender GravityZone Install** and set timeout for 1800 seconds.

**Install time will vary based on internet speed and other AV removal by BitDefender BEST deployment**
