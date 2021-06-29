# Global Key Store

The key store is used to store values that need to be referenced from multiple scripts. This also allows for easy updating of values since scripts reference the values at runtime.

To Add/Edit values in the Global Key Store, browse to **Settings > Global Settings > KeyStore**. 

You can reference values from the key store in script arguments by using the {{global.key_name}} syntax.

!!!info
    Everything between {{}} is CaSe sEnSiTive

See [Scripts](scripting.md) for more information.