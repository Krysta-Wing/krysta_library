class KrystaError(Exception):
    pass

class KrystaTimeoutError(KrystaError):
    pass

class KrystaGatewayError(KrystaError):
    pass

class KrystaSandboxError(KrystaError):
    pass
