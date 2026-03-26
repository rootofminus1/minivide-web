import os
import pulumi
import pulumi_aws as aws
from pulumi import FileArchive

LAYERS_DIR = os.path.join(os.path.dirname(__file__), "../ffmpg/ffmpeg-layer.zip")

def make_layer(resource_name: str, zip_path: str) -> aws.lambda_.LayerVersion:
    return aws.lambda_.LayerVersion(
        resource_name,
        code=FileArchive(zip_path),                                  
        layer_name=f"{resource_name}",                               
        compatible_runtimes=[aws.lambda_.Runtime.PYTHON3D14.value],  
        compatible_architectures=["x86_64", "arm64"],                
    )

ffmpeg_layer = make_layer("ffmpeg-layer", LAYERS_DIR)
