#
#  Copyright 2019 The FATE Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from .dataframe_io_test import dataframe_io_test
from .dataframe_transformer import dataframe_transformer
from .demo import run
from .evaluation import evaluation
from .feature_scale import feature_scale
from .hetero_lr import hetero_lr
from .intersection import intersection
from .multi_model_test import multi_model_test
from .reader import reader
from .statistics import statistics

BUILDIN_COMPONENTS = [
    hetero_lr,
    reader,
    feature_scale,
    intersection,
    evaluation,
    run,
    dataframe_transformer,
    statistics,
    dataframe_io_test,
    multi_model_test,
]
