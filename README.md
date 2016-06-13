# gdistcc




### Sample ~/.ssh/config

```
Host *.gdistcc
        ControlMaster auto
        ControlPath ~/.ssh/%r@%h:%p
        ControlPersist 5m
        Ciphers aes256-gcm@openssh.com
        StrictHostKeyChecking no
        UserKnownHostsFile=/dev/null
```
