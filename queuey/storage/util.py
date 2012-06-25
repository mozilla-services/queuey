"""Storage utility functions"""
from cdecimal import Decimal
import random
import uuid

DECIMAL_1E7 = Decimal('1e7')

# This function copied from pycassa, under MIT license
# Copyright (c) 2009 Jonathan Hseu
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
# to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


def convert_time_to_uuid(time_arg, lowest_val=True, randomize=False):
    """
    Converts a timestamp to a type 1 :class:`uuid.UUID`.

    This is to assist with getting a time slice of columns or creating
    columns when column names are ``TimeUUIDType``. Note that this is done
    automatically in most cases if name packing and value packing are
    enabled.

    Also, be careful not to rely on this when specifying a discrete
    set of columns to fetch, as the non-timestamp portions of the
    UUID will be generated randomly. This problem does not matter
    with slice arguments, however, as the non-timestamp portions
    can be set to their lowest or highest possible values.

    :param time_arg:
      The time to use for the timestamp portion of the UUID.
      Expected inputs to this would either be a :class:`decimal` object or
      a timestamp with a precision of at most 100 nanoseconds.
      Sub-second precision should be below the decimal place.
    :type time_arg: :class:`decimal` or timestamp

    :param lowest_val:
      Whether the UUID produced should be the lowest possible value
      UUID with the same timestamp as time_arg or the highest possible
      value.
    :type lowest_val: bool

    :param randomize:
      Whether the clock and node bits of the UUID should be randomly
      generated.  The `lowest_val` argument will be ignored if this
      is true.
    :type randomize: bool

    :rtype: :class:`uuid.UUID`

    """
    if isinstance(time_arg, uuid.UUID):
        return time_arg
    if isinstance(time_arg, float):
        time_arg = Decimal.from_float(time_arg)

    ns_100 = int(time_arg * DECIMAL_1E7)

    # 0x01b21dd213814000 is the number of 100-ns intervals between the
    # UUID epoch 1582-10-15 00:00:00 and the Unix epoch 1970-01-01 00:00:00.
    timestamp = ns_100 + 0x01b21dd213814000L

    time_low = timestamp & 0xffffffffL
    time_mid = (timestamp >> 32L) & 0xffffL
    time_hi_version = (timestamp >> 48L) & 0x0fffL

    if randomize:
        rand_bits = random.getrandbits(8 + 8 + 48)
        clock_seq_low = rand_bits & 0xffL  # 8 bits, no offset
        clock_seq_hi_variant = (rand_bits & 0xff00L) / 0x100  # 8 bits, 8 offset
        node = (rand_bits & 0xffffffffffff0000L) / 0x10000L  # 48 bits, 16 offset
    else:
        # In the event of a timestamp tie, Cassandra compares the two
        # byte arrays directly. This is a *signed* comparison of each byte
        # in the two arrays.  So, we have to make each byte -128 or +127 for
        # this to work correctly.
        #
        # For the clock_seq_hi_variant, we don't get to pick the two most
        # significant bits (they're always 01), so we are dealing with a
        # positive byte range for this particular byte.
        if lowest_val:
            # Make the lowest value UUID with the same timestamp
            clock_seq_low = 0x80L
            clock_seq_hi_variant = 0 & 0x3fL  # The two most significant bits
                                              # will be 0 and 1, no matter what
            node = 0x808080808080L  # 48 bits
        else:  # pragma: nocover
            # Make the highest value UUID with the same timestamp
            clock_seq_low = 0x7fL
            clock_seq_hi_variant = 0x3fL  # The two most significant bits will
                                          # 0 and 1, no matter what
            node = 0x7f7f7f7f7f7fL  # 48 bits
    return uuid.UUID(fields=(time_low, time_mid, time_hi_version,
                        clock_seq_hi_variant, clock_seq_low, node), version=1)
