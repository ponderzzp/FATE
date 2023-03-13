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
#
import numpy as np
import operator
import pandas as pd

from typing import Any, List, Union, Dict

from .ops import (
    aggregate_indexer,
    transform_to_tensor,
    transform_to_table,
    get_partition_order_mappings,
    select_column_value
)
from .manager import DataManager, Schema


class DataFrame(object):
    def __init__(self, ctx, block_table, partition_order_mappings, data_manager: DataManager):
        self._ctx = ctx
        self._block_table = block_table
        self._partition_order_mappings = partition_order_mappings
        self._data_manager = data_manager

        """
        the following is cached
        index: [(id, (partition_id, index_in_block)]
        """
        self._sample_id_indexer = None
        self._match_id_indexer = None
        self._sample_id = None
        self._match_id = None
        self._label = None
        self._weight = None

        self.__count = None
        self._columns = None

    @property
    def sample_id(self):
        if self._sample_id is None:
            self._sample_id = self.__extract_fields(with_sample_id=True,
                                                    with_match_id=False,
                                                    with_label=False,
                                                    with_weight=False)
        return self._sample_id

    @property
    def match_id(self):
        if self._match_id is None:
            self._match_id = self.__extract_fields(with_sample_id=True,
                                                   with_match_id=True,
                                                   with_label=False,
                                                   with_weight=False)

        return self._match_id

    @property
    def values(self):
        """
        as values maybe bigger than match_id/sample_id/weight/label, we will not cached them
        """
        if not len(self.schema.columns):
            return None

        return self.__extract_fields(
            with_sample_id=False,
            with_match_id=False,
            with_label=False,
            with_weight=False,
            columns=self.columns.tolist()
        )

    @property
    def label(self):
        if not self.schema.label_name:
            return None

        if self._label is None:
            self._label = self.__extract_fields(
                with_sample_id=True,
                with_match_id=True,
                with_label=True,
                with_weight=False
            )

        return self._label

    @property
    def weight(self):
        if not self.schema.weight_name:
            return None

        if self._weight is None:
            self._weight = self.__extract_fields(
                with_sample_id=True,
                with_match_id=True,
                with_label=False,
                with_weight=False
            )

        return self._weight

    @property
    def shape(self) -> "tuple":
        if not self.__count:
            if self._sample_id_indexer:
                items = self._sample_id_indexer.count()
            elif self._match_id_indexer:
                items = self._match_id_indexer.count()
            else:
                items = self._block_table.mapValues(lambda block: 0 if block is None else len(block[0])).reduce(
                    lambda size1, size2: size1 + size2)
            self.__count = items

        return self.__count, len(self._data_manager.schema.columns)

    @property
    def schema(self) -> "Schema":
        return self._data_manager.schema

    @property
    def columns(self):
        return self.schema.columns

    @property
    def block_table(self):
        return self._block_table

    @property
    def partition_order_mappings(self):
        return self._partition_order_mappings

    @property
    def data_manager(self) -> "DataManager":
        return self._data_manager

    def as_tensor(self, dtype=None):
        """
        df.weight.as_tensor()
        df.label.as_tensor()
        df.values.as_tensor()
        """
        attr_status = 0
        if self.schema.label_name:
            attr_status |= 1

        if self.schema.weight_name:
            attr_status |= 2

        if len(self.schema.columns):
            attr_status |= 4

        if attr_status == 0:
            raise ValueError(f"label/weight/values attributes are None")

        if attr_status & -attr_status != attr_status:
            raise ValueError(f"Use df.label.as_tensor() or df.weight.as_tensor() or df.values.as_tensor(), "
                             f"don't mixed please")

        if attr_status == 1:
            return self.__convert_to_tensor(self.schema.label_name, dtype=dtype)
        elif attr_status == 1:
            return self.__convert_to_tensor(self.schema.weight_name, dtype=dtype)
        else:
            return self.__convert_to_tensor(self.schema.columns.tolist(), dtype=dtype)

    def as_pd_df(self) -> "pd.DataFrame":
        from .ops._transformer import transform_to_pandas_dataframe
        return transform_to_pandas_dataframe(
            self._block_table,
            self._data_manager
        )

    def create_frame(self, with_label=False, with_weight=False, columns: list = None) -> "DataFrame":
        return self.__extract_fields(with_sample_id=True,
                                      with_match_id=True,
                                      with_label=with_label,
                                      with_weight=with_weight,
                                      columns=columns)


    def max(self, *args, **kwargs) -> "DataFrame":
        ...

    def min(self, *args, **kwargs) -> "DataFrame":
        ...

    def mean(self, *args, **kwargs) -> "DataFrame":
        ...

    def sum(self, *args, **kwargs) -> "DataFrame":
        ...

    def std(self, *args, **kwargs) -> "DataFrame":
        ...

    def count(self) -> "int":
        return self.shape[0]

    def quantile(self, q, axis=0, method="quantile", ):
        ...

    def __add__(self, other: Union[int, float, list, "np.ndarray", "DataFrame"]) -> "DataFrame":
        return self.__arithmetic_operate(operator.add, other)

    def __radd__(self, other: Union[int, float, list, "np.ndarray"]) -> "DataFrame":
        return self + other

    def __sub__(self, other: Union[int, float, list, "np.ndarray"]) -> "DataFrame":
        return self.__arithmetic_operate(operator.sub, other)

    def __rsub__(self, other: Union[int, float, list, "np.ndarray"]) -> "DataFrame":
        return self * (-1) + other

    def __mul__(self, other) -> "DataFrame":
        return self.__arithmetic_operate(operator.mul, other)

    def __rmul__(self, other) -> "DataFrame":
        return self * other

    def __truediv__(self, other) -> "DataFrame":
        return self.__arithmetic_operate(operator.truediv, other)

    def __lt__(self, other) -> "DataFrame":
        ...

    def __le__(self, other) -> "DataFrame":
        ...

    def __gt__(self, other) -> "DataFrame":
        ...

    def __ge__(self, other) -> "DataFrame":
        ...

    def __arithmetic_operate(self, op, other) -> "DataFrame":
        """
        df * 1.5, int -> float
        可能的情况：
        a. columns类型统一：此时，block只有一个
        b. columns类型不一致，多block，但要求单个block里面所有列都是被使用的。

        需要注意的是：int/float可能会统一上升成float，所以涉及到block类型的变化和压缩
        """
        from .ops._arithmetic import arith_operate
        return arith_operate(self, other, op)

    def __cmp_operate(self, op, other) -> "DataFrame":
        ...

    def __getattr__(self, attr):
        if attr not in self._data_manager.schema.columns:
            raise ValueError(f"DataFrame does not has attribute {attr}")

        assert 1 == 2

    def __getitem__(self, items) -> "DataFrame":
        if not isinstance(items, list):
            items = [items]

        for item in items:
            if item not in self._data_manager.schema.columns:
                raise ValueError(f"DataFrame does not has attribute {item}")

        return self.__extract_fields(with_sample_id=True, with_match_id=True, columns=items)

    def __setitem__(self, keys, items) -> "DataFrame":
        if isinstance(keys, str):
            keys = [keys]

        state = 0
        column_set = set(self._data_manager.schema.columns)
        for key in keys:
            if key not in column_set:
                state |= 1
            else:
                state |= 2

        if state == 3:
            raise ValueError(f"setitem operation does not support a mix of old and new columns")

        from .ops._set_item import set_item

        self._block_table = set_item(self, keys, items, state)

    def __len__(self):
        return self.count()

    def _retrieval_attr(self) -> dict:
        return dict(
            ctx=self._ctx,
            schema=self._schema.dict(),
            index=self._index,
            values=self._values,
            label=self._label,
            weight=self._weight,
        )

    def __get_index_by_column_names(self, column_names):
        if isinstance(column_names, str):
            column_names = [column_names]

        indexes = []
        header_mapping = dict(zip(self._schema.header, range(len(self._schema.header))))
        for col in column_names:
            index = header_mapping.get(col, None)
            if index is None:
                raise ValueError(f"Can not find column: {col}")
            indexes.append(index)

        return indexes

    def get_indexer(self, target):
        if target not in ["sample_id", "match_id"]:
            raise ValueError(f"Target should be sample_id or match_id, but {target} found")

        target_name = getattr(self.schema, f"{target}_name")
        indexer = self.__convert_to_table(target_name)
        if target == "sample_id":
            self._sample_id_indexer = indexer
        else:
            self._match_id_indexer = indexer

        return indexer

    def loc(self, indexer, target="sample_id", preserve_order=False):
        self_indexer = self.get_indexer(target)
        if preserve_order:
            indexer = self_indexer.join(indexer, lambda lhs, rhs: (lhs, rhs))
        else:
            indexer = self_indexer.join(indexer, lambda lhs, rhs: (lhs, lhs))

        agg_indexer = aggregate_indexer(indexer)

        if not preserve_order:
            def _convert_block(blocks, retrieval_indexes):
                row_indexes = [retrieval_index[0] for retrieval_index in retrieval_indexes]
                return [block[row_indexes] for block in blocks]

            block_table = self._block_table.join(agg_indexer, _convert_block)
        else:
            def _convert_to_block(kvs):
                ret_dict = {}
                for block_id, (blocks, block_indexer) in kvs:
                    """
                    block_indexer: row_id, (new_block_id, new_row_id)
                    """
                    for src_row_id, (dst_block_id, dst_row_id) in block_indexer:
                        if dst_block_id not in ret_dict:
                            ret_dict[dst_block_id] = []

                        ret_dict[dst_block_id].append([block[src_row_id] if isinstance(block, pd.Index)
                                                       else block[src_row_id].tolist() for block in blocks])

                return list(ret_dict.items())

            def _merge_list(lhs, rhs):
                if not lhs:
                    return rhs
                if not rhs:
                    return lhs

                l_len = len(lhs)
                r_len = len(rhs)
                ret = [[] for i in range(l_len + r_len)]
                i, j, k = 0, 0, 0
                while i < l_len and j < r_len:
                    if lhs[i][0] < rhs[j][0]:
                        ret[k] = lhs[i]
                        i += 1
                    else:
                        ret[k] = rhs[j]
                        j += 1

                    k += 1

                while i < l_len:
                    ret[k] = lhs[i]
                    i += 1
                    k += 1

                while j < r_len:
                    ret[k] = rhs[j]
                    j += 1
                    k += 1

                return ret

            from .ops._transformer import transform_list_block_to_frame_block
            block_table = self._block_table.join(agg_indexer, lambda lhs, rhs: (lhs, rhs))
            block_table = block_table.mapReducePartitions(_convert_to_block, _merge_list)
            block_table = transform_list_block_to_frame_block(block_table,
                                                              self._data_manager)

        partition_order_mappings = get_partition_order_mappings(block_table)
        return DataFrame(self._ctx,
                         block_table,
                         partition_order_mappings,
                         self._data_manager)

    def iloc(self, indexes):
        ...

    @classmethod
    def hstack(cls, stacks: List["DataFrame"]) -> "DataFrame":
        ...

    def __extract_fields(self, with_sample_id=True, with_match_id=True,
                         with_label=True, with_weight=True, columns: Union[str, list] = None) -> "DataFrame":
        from .ops._field_extract import field_extract
        return field_extract(
            self,
            with_sample_id=with_sample_id,
            with_match_id=with_match_id,
            with_label=with_label,
            with_weight=with_weight,
            columns=columns
        )

    def __convert_to_tensor(self, columns: Union[str, list], dtype: str = None):
        if isinstance(columns, str):
            columns = [columns]

        column_index_offsets = [self._schema_manager.get_column_offset(column) for column in columns]
        block_indexes = [self._block_manager.get_block_id(column) for column in column_index_offsets]
        _, block_retrieval_indexes = self._block_manager.derive_new_block_manager(column_index_offsets)

        return transform_to_tensor(
            self._ctx,
            self._block_table,
            block_indexes,
            block_retrieval_indexes,
            dtype=dtype)

    def __convert_to_table(self, target_name):
        block_loc = self._data_manager.loc_block(target_name)
        assert block_loc[1] == 0, "support only one indexer in current version"

        return transform_to_table(self._block_table, block_loc[0], self._partition_order_mappings)

    def to_secure_boost_frame(self):
        return SecureBoostFrame(
            self._ctx,
            self._block_table,
            self._partition_order_mappings,
            self._data_manager
        )


class SecureBoostFrame(DataFrame):
    def apply_node_map(self, node_map_dict: Dict[Any, Any]) -> "DataFrame":
        """
        值替换，比如(0, True)->1，(0, False)->2表示分裂到下一层怎么走
        """
        ...

    def apply_select(self, target: Union["DataFrame", "SecureBoostFrame"]):
        """
        根据DataFrame的列取出对应特征列的值，该算子不放到storage层实现，涉及到每行可能特征会不一样
        """
        if len(target.schema.columns) != 1:
            raise ValueError("To use apply_select, target's should has only one column")

        other_column_name = target.schema.columns[0]
        target_block_id = target.data_manager.loc_block(other_column_name)
        offset = target.schema_manager.get_column_offset(other_column_name)
        target_block_id = target.block_manager.get_block_id(offset)

        non_operable_column_offsets = self._schema_manager.infer_non_operable_column_offsets()
        non_operable_blocks = [
            self._block_manager.get_block_id(column_offset)[0] for column_offset in non_operable_column_offsets
        ]

        select_column_value(
            self._block_table,
            target.block_table,
            target_block_id,
            non_operable_blocks,
            self._schema_manager,
            self._block_manager
        )

        return SecureBoostFrame(
            self._ctx,
            target_block_id,
            self._partition_order_mappings,
            ...,
        )
