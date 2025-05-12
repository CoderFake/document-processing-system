import grpc
import warnings

from utils import word_pb2 as word__pb2

GRPC_GENERATED_VERSION = '1.71.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    warnings.warn(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in word_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
    )


class WordServiceStub(object):
    """Dịch vụ chuyển đổi tài liệu Word."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ConvertToPDF = channel.unary_unary(
                '/mscword.WordService/ConvertToPDF',
                request_serializer=word__pb2.ConvertRequest.SerializeToString,
                response_deserializer=word__pb2.ConvertReply.FromString,
                _registered_method=True)


class WordServiceServicer(object):
    """Dịch vụ chuyển đổi tài liệu Word."""

    def ConvertToPDF(self, request, context):
        """Chuyển đổi tệp Word sang PDF."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_WordServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ConvertToPDF': grpc.unary_unary_rpc_method_handler(
                    servicer.ConvertToPDF,
                    request_deserializer=word__pb2.ConvertRequest.FromString,
                    response_serializer=word__pb2.ConvertReply.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'mscword.WordService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('mscword.WordService', rpc_method_handlers)


class WordService(object):
    """Dịch vụ chuyển đổi tài liệu Word."""

    @staticmethod
    def ConvertToPDF(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mscword.WordService/ConvertToPDF',
            word__pb2.ConvertRequest.SerializeToString,
            word__pb2.ConvertReply.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True) 