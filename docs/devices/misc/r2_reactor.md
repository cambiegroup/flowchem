# Vapourtec R2 reactor

The Vapourtec R2 reactor is a complex device that integrates several independent components.

```{note}
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
* timeout 0.1s
* baudrate 19200
* parity none
* stopbits 1
* bytesize 8
```
