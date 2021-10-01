# Examples

## Create Run URL Action to Computer support page

This will create a URL link that will take you to the support page for a computer based on the computers Serial Number

1. Goto `Settings | Global Settings | Custom Fields` 
    
    Under Agents tab Add Custom Field (CaSe SeNsItIve)

    ![Custom Field](../images/example1_customfield.png)

2. Create Task (best to use `Settings | Automation Manager` if you want to apply it to all computers). Add script that has an output of the data you want.

    ![Collector Script](../images/example1_taskcollectorscript.png)

3. Create URL Action (under `Settings | Global Settings | URL ACTIONS`) for Manufacturer websites

    ![URL Actions](../images/example1_urlaction.png)

Dell Support Page

```
https://www.dell.com/support/home/en-us/product-support/servicetag/{{agent.SerialNumber}}/overview
```

Lenovo  Support Page

```
https://pcsupport.lenovo.com/us/en/products/{{agent.SerialNumber}}
```

HP Support Page

It gives an errors because the product model doesn't match the serial number. If you figure out a better link please let us know! :)

```
https://support.hp.com/us-en/product/hp-pro-3500-microtower-pc/5270849/model/5270850?serialnumber={{agent.SerialNumber}}
```
