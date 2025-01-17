import socket
import asyncio
from typing import Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class ProtocolResult:
    success: bool
    response_time: float
    error: Optional[str] = None
    response: Optional[bytes] = None

class BaseProtocol(ABC):
    @abstractmethod
    async def send_request(self, target: str, port: int) -> ProtocolResult:
        pass

class TCPProtocol(BaseProtocol):
    async def send_request(self, target: str, port: int) -> ProtocolResult:
        try:
            start_time = asyncio.get_event_loop().time()
            
            reader, writer = await asyncio.open_connection(target, port)
            
            # Send a simple probe message
            message = b"PROBE\n"
            writer.write(message)
            await writer.drain()
            
            # Wait for response with timeout
            response = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            
            writer.close()
            await writer.wait_closed()
            
            end_time = asyncio.get_event_loop().time()
            return ProtocolResult(
                success=True,
                response_time=end_time - start_time,
                response=response
            )
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            return ProtocolResult(
                success=False,
                response_time=end_time - start_time,
                error=str(e)
            )

class UDPProtocol(BaseProtocol):
    async def send_request(self, target: str, port: int) -> ProtocolResult:
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Create UDP socket
            transport, protocol = await asyncio.get_event_loop().create_datagram_endpoint(
                lambda: UDPClientProtocol(),
                remote_addr=(target, port)
            )
            
            # Send data
            transport.sendto(b"PROBE\n")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(protocol.receive(), timeout=5.0)
            except asyncio.TimeoutError:
                response = None
            
            transport.close()
            
            end_time = asyncio.get_event_loop().time()
            return ProtocolResult(
                success=True if response else False,
                response_time=end_time - start_time,
                response=response
            )
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            return ProtocolResult(
                success=False,
                response_time=end_time - start_time,
                error=str(e)
            )

class UDPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.response_future = asyncio.Future()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.response_future.set_result(data)

    def error_received(self, exc):
        self.response_future.set_exception(exc)

    async def receive(self):
        return await self.response_future 