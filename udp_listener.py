import socket, io, asyncio, time, sys, os #pygame
import ctypes, ctypes.util
from ctypes import Structure, POINTER
ct = ctypes
from typing import Any

request = b"DSUC\351\003\f\000\016\363\371\333\000\000\000\000\002\000\020\000\001\000\000\000\000\000\000\000"

operator = None
props = None
addr = None

def mix(a, b, fac):
    return (1-fac)*a + b*fac

class cancelledError(Exception):
    pass

class Structure(Structure): # https://stackoverflow.com/a/25892189
    _defaults_ = {}
    def __init__(self, **kwargs):
        values = type(self)._defaults_.copy()
        values.update(kwargs)
        super().__init__(**values)

class Controller(Structure): # thank you chatgpt
    # i gave it the raw structure from the ds4windows repo and so it could convert it to a ctypes structure for me lol
    _pack_ = 1
    _fields_ = [
        # Header section
        ("initCode", ctypes.c_ubyte * 4), # 0
        ("protocolVersion", ctypes.c_ushort), # 4
        ("messageLen", ctypes.c_ushort), # 6
        ("crc", ctypes.c_int), # 8
        ("serverId", ctypes.c_uint), # 
        ("messageType", ctypes.c_uint),
        
        # Pad meta section
        ("padId", ctypes.c_ubyte),
        ("padState", ctypes.c_ubyte),
        ("model", ctypes.c_ubyte),
        ("connectionType", ctypes.c_ubyte),
        ("address", ctypes.c_ubyte * 6),
        ("batteryStatus", ctypes.c_ubyte),
        ("isActive", ctypes.c_ubyte),
        ("packetCounter", ctypes.c_uint),
        
        # Primary controls
        ("buttons1", ctypes.c_ubyte),
        ("buttons2", ctypes.c_ubyte),
        ("Home", ctypes.c_ubyte),
        ("touchButton", ctypes.c_ubyte),
        ("lx", ctypes.c_ubyte),
        ("ly", ctypes.c_ubyte),
        ("rx", ctypes.c_ubyte),
        ("ry", ctypes.c_ubyte),
        ("dpadLeft", ctypes.c_ubyte),
        ("dpadDown", ctypes.c_ubyte),
        ("dpadRight", ctypes.c_ubyte),
        ("dpadUp", ctypes.c_ubyte),
        ("square", ctypes.c_ubyte),
        ("cross", ctypes.c_ubyte),
        ("circle", ctypes.c_ubyte),
        ("triangle", ctypes.c_ubyte),
        ("r1", ctypes.c_ubyte),
        ("l1", ctypes.c_ubyte),
        ("r2", ctypes.c_ubyte),
        ("l2", ctypes.c_ubyte),
        
        # Touch 1
        ("touch1Active", ctypes.c_ubyte),
        ("touch1PacketId", ctypes.c_ubyte),
        ("touch1X", ctypes.c_ushort),
        ("touch1Y", ctypes.c_ushort),
        
        # Touch 2
        ("touch2Active", ctypes.c_ubyte),
        ("touch2PacketId", ctypes.c_ubyte),
        ("touch2X", ctypes.c_ushort),
        ("touch2Y", ctypes.c_ushort),
        
        # Accel
        ("totalMicroSec", ctypes.c_ulonglong),
        ("accelXG", ctypes.c_float),
        ("accelYG", ctypes.c_float),
        ("accelZG", ctypes.c_float),
        
        # Gyro
        ("angVelPitch", ctypes.c_float),
        ("angVelYaw", ctypes.c_float),
        ("angVelRoll", ctypes.c_float)
    ]

controllers = {i: [Controller(), 0, False] for i in range(4)}

#CC = Controller()
#CC.

#pygame.init()
W = 1600
H = 900
#screen = pygame.display.set_mode((W, H))
#clock = pygame.time.Clock()


#sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#addr = ('127.0.0.1', 26760)

t1 = time.time()
smooth_rate = 0
last = 0

async def pygame_debug():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()
    #try:
    while True:
        screen.fill('black')
        if len(controllers) == 0:
            await asyncio.sleep(1/60)
            continue
        c = controllers[0]
        font = pygame.font.SysFont('arialbd.ttf', 15)
        n = 0
        for prop in dir(c):
            if prop.startswith('_'): continue
            v = getattr(c, prop)
            img = font.render(f'{prop}: {v}', True, 'white')
            screen.blit(img, (10, n*15))
            n += 1
        for event in pygame.event.get():
            pass
        pygame.display.update()
        await asyncio.sleep(1/60)
    pass
    #except Exception as e:
    #    print(e)

class AsyncUDP(asyncio.DatagramProtocol):

    def __init__(self) -> None:
        super().__init__()
        self.error = False

    def error_received(self, exc: Exception) -> None:
        self.error = True
        self.transport.close()
        self.transport.abort()
        #raise exc

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport

    def connection_lost(self, exc: Exception | None) -> None:
        print('goodbye!')
        #raise cancelledError

    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        global last

        if not props.running:
            self.transport.close()
            self.transport.abort()
            return
        
        if props.server_fail:
            operator.report({'INFO'}, 'Connected to UDP server!')
            print('Successfully connected to UDP server')

        props.server_fail = False
        padId = int(data[20])
        Con = controllers.get(padId)
        ctypes.memmove(ctypes.addressof(Con[0]), data, len(data))
        Con[1] = time.time()
        Con[2] = True
        return
        for prop in dir(data):
            if prop.startswith('_'): continue
            v = getattr(data, prop)
            if not type(v) in {float}: continue

async def write_messages(sock):
    while True:
        #if time.time() - last > 3:
        #    print('writer out of time!')
        #    return
        try:
            sock.sendto(request, addr)
        except OSError:
            print('UDP Write error. Cancelling, assuming server is not open.')
            return
        await asyncio.sleep(1)

async def establish_udp_receiver():
    loop = asyncio.get_event_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_listener = await loop.create_datagram_endpoint(lambda: AsyncUDP(), sock=sock)
    return udp_listener

async def udp_looper():
    global last
    print('running!')
    loop = asyncio.get_event_loop()
    while True:
        last = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_listener = loop.create_datagram_endpoint(AsyncUDP, sock=sock)
        udp = asyncio.create_task(udp_listener)
        writer = asyncio.create_task(write_messages(sock))

        done, pending = await asyncio.wait([udp, writer], return_when=asyncio.FIRST_EXCEPTION)
        
        if not props.server_fail and props.running:
            operator.report({'WARNING'}, 'Lost connection to UDP server! Are any controllers connected?')
        
        props.server_fail = True

        for task in pending:
            task.cancel()

        await asyncio.gather(*pending, return_exceptions=False)

        if not props.running:
            print('Universal Remote session ended')
            return

async def controller_timeout():
    while True:
        await asyncio.sleep(1)
        print(controllers)
        for num, con_data in list(controllers.items()):
            if time.time() - con_data[1] < 3:
                controllers[num][2] = True
                continue
            controllers[num][2] = False

def start_udp_listener(p, op):
    global props
    global operator
    global addr

    props = p
    operator = op
    addr = (p.udp_addr, int(p.udp_port))

    #async def main():
    #    await udp_looper()

    asyncio.run(udp_looper())
