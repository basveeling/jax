# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from absl.testing import absltest, parameterized
import numpy as np

import jax
from jax.config import config
import jax.dlpack
import jax.numpy as jnp
from jax import test_util as jtu

config.parse_flags_with_absl()

try:
  import torch
  import torch.utils.dlpack
except ImportError:
  torch = None


scalar_types = [jnp.bool_, jnp.int8, jnp.int16, jnp.int32, jnp.int64,
                jnp.uint8, jnp.uint16, jnp.uint32, jnp.uint64,
                jnp.bfloat16, jnp.float16, jnp.float32, jnp.float64]
torch_types = [jnp.int8, jnp.int16, jnp.int32, jnp.int64,
               jnp.uint8, jnp.float16, jnp.float32, jnp.float64]

nonempty_nonscalar_array_shapes = [(4,), (3, 4), (2, 3, 4)]
empty_array_shapes = []
# TODO(phawkins): size 0 and 1 dimensions are mishandled (with an error) when
# being imported to JAX in jaxlib 0.1.38.
if jax.lib.version > (0, 1, 38):
  empty_array_shapes += [(0,), (0, 4), (3, 0),]
  nonempty_nonscalar_array_shapes += [(3, 1), (1, 4), (2, 1, 4)]

nonempty_array_shapes = [()] + nonempty_nonscalar_array_shapes
all_shapes = nonempty_array_shapes + empty_array_shapes

class DLPackTest(jtu.JaxTestCase):
  def setUp(self):
    if jtu.device_under_test() == "tpu":
      self.skipTest("DLPack not supported on TPU")

  @parameterized.named_parameters(jtu.cases_from_list(
     {"testcase_name": "_{}".format(
        jtu.format_shape_dtype_string(shape, dtype)),
     "shape": shape, "dtype": dtype}
     for shape in all_shapes
     for dtype in scalar_types))
  def testJaxRoundTrip(self, shape, dtype):
    rng = jtu.rand_default()
    np = rng(shape, dtype)
    x = jnp.array(np)
    dlpack = jax.dlpack.to_dlpack(x)
    y = jax.dlpack.from_dlpack(dlpack)
    self.assertAllClose(x, y, check_dtypes=True)

    self.assertRaisesRegex(RuntimeError,
                           "DLPack tensor may be consumed at most once",
                           lambda: jax.dlpack.from_dlpack(dlpack))

  @parameterized.named_parameters(jtu.cases_from_list(
     {"testcase_name": "_{}".format(
        jtu.format_shape_dtype_string(shape, dtype)),
     "shape": shape, "dtype": dtype}
     for shape in all_shapes
     for dtype in torch_types))
  @unittest.skipIf(not torch, "Test requires PyTorch")
  def testTorchToJax(self, shape, dtype):
    rng = jtu.rand_default()
    np = rng(shape, dtype)
    x = torch.from_numpy(np)
    x = x.cuda() if jtu.device_under_test() == "gpu" else x
    dlpack = torch.utils.dlpack.to_dlpack(x)
    y = jax.dlpack.from_dlpack(dlpack)
    self.assertAllClose(np, y, check_dtypes=True)

  @parameterized.named_parameters(jtu.cases_from_list(
     {"testcase_name": "_{}".format(
        jtu.format_shape_dtype_string(shape, dtype)),
     "shape": shape, "dtype": dtype}
     for shape in all_shapes
     for dtype in torch_types))
  @unittest.skipIf(not torch or jax.lib.version <= (0, 1, 38),
                   "Test requires PyTorch and jaxlib >= 0.1.39")
  # TODO(phawkins): the dlpack destructor issues errors in jaxlib 0.1.38.
  def testJaxToTorch(self, shape, dtype):
    rng = jtu.rand_default()
    np = rng(shape, dtype)
    x = jnp.array(np)
    dlpack = jax.dlpack.to_dlpack(x)
    y = torch.utils.dlpack.from_dlpack(dlpack)
    self.assertAllClose(np, y.numpy(), check_dtypes=True)


if __name__ == "__main__":
  absltest.main()
