import os

import torch
import torchaudio
import torchvision


def cut_or_pad(data, size, dim=0):
    """
    Pads or trims the data along a dimension.
    """
    if data.size(dim) < size:
        padding = size - data.size(dim)
        data = torch.nn.functional.pad(data, (0, padding), "constant")
    elif data.size(dim) > size:
        data = data[:size]
    assert data.size(dim) == size
    return data


def load_video(path):
    """
    rtype: torch, T x C x H x W
    """
    vid = torchvision.io.read_video(path, pts_unit="sec", output_format="THWC")[0]
    vid = vid.permute((0, 3, 1, 2))
    return vid


def load_audio(path):
    """
    rtype: torch, T x 1
    """
    waveform, sample_rate = torchaudio.load(path[:-4] + ".wav", normalize=True)
    return waveform.transpose(1, 0)


class AVDataset(torch.utils.data.Dataset):
    def __init__(
        self,
        root,
        label_path,
        subset,
        modality,
        audio_transform,
        video_transform,
        rate_ratio=640,
        max_frame=1800,
        max_length=100,
    ):

        self.root = root

        self.modality = modality
        self.rate_ratio = rate_ratio
        self.max_frame = int(max_frame)
        self.max_length = int(max_length)

        self.list = self.load_list(label_path)

        self.audio_transform = audio_transform
        self.video_transform = video_transform
        

    def load_list(self, label_path):
        paths_counts_labels = []
        for path_count_label in open(label_path).read().splitlines():
            dataset_name, rel_path, input_length, token_id = path_count_label.split(",")
            if int(input_length) < self.max_frame and int(input_length) < self.max_length:
                path = os.path.join(self.root, dataset_name, rel_path)
                if os.path.exists(path):
                    token = [int(_) for _ in token_id.split()]
                    if len(token) < 1:
                        continue
                    paths_counts_labels.append(
                        (
                            dataset_name,
                            rel_path,
                            int(input_length),
                            torch.tensor([int(_) for _ in token_id.split()]),
                        )
                    )
        return paths_counts_labels

    def __getitem__(self, idx):
        dataset_name, rel_path, input_length, token_id = self.list[idx]
        path = os.path.join(self.root, dataset_name, rel_path)
        if self.modality == "video":
            video = load_video(path)
            video = self.video_transform(video)
            return {"input": video, "target": token_id}
        elif self.modality == "audio":
            audio = load_audio(path)
            audio = self.audio_transform(audio)
            return {"input": audio, "target": token_id}
        elif self.modality == "audiovisual":
            video = load_video(path)
            audio = load_audio(path)
            audio = cut_or_pad(audio, len(video) * self.rate_ratio)
            video = self.video_transform(video)
            audio = self.audio_transform(audio)
            return {"video": video, "audio": audio, "target": token_id}

    def __len__(self):
        return len(self.list)
