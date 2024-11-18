import torch
from torchvision import transforms
from PIL import Image


def run_model(image_path, model_path="road_condition_model.pth"):
    model = torch.load(model_path)
    model.eval()

    transform = transforms.Compose(
        [transforms.Resize((224, 224)), transforms.ToTensor()]
    )

    image = Image.open(image_path).convert("RGB")
    input_tensor = transform(image).unsqueeze(0)
    result = model(input_tensor)
    return torch.argmax(result, dim=1).item()  # Example classification result
