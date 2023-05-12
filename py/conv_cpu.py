"""Convolution methods on CPU."""
# These are extremely slow.
# Their main purpose is testing fast GPU implementations.

import numpy as np

def DivUp(a, b):
  return (a + b - 1) / b

def ConvUp(images, filters, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  output = np.zeros((num_images, num_modules_x * num_modules_y * num_output_channels), dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):
      input_data = np.zeros((num_images, kernel_size_x * kernel_size_y * num_input_channels), dtype=np.float32)

      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y
      offset = y_pos * num_modules_x + x_pos

      for c in xrange(num_input_channels):
        for y in xrange(start_y, start_y + kernel_size_y):
          if y < 0 or y >= image_size_y:
            continue
          for x in xrange(start_x, start_x + kernel_size_x):
            if x < 0 or x >= image_size_x:
              continue
            input_data_x = x - start_x
            input_data_y = y - start_y
            input_data_index = (c * kernel_size_y + input_data_y) * kernel_size_x + input_data_x
            images_index     = (c * image_size_y  +            y) * image_size_x  +            x
            input_data[:, input_data_index] = images[:, images_index]
      output_data = np.dot(input_data, filters.T)

      for c in xrange(num_output_channels):
        output[:, offset + c * num_modules_x * num_modules_y] = output_data[:, c]
  return output

def ConvDown(derivs, filters, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  output = np.zeros((num_images, image_size_x * image_size_y * num_input_channels), dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):
      deriv = np.zeros((num_images, num_output_channels), dtype=np.float32)
      
      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y
      offset = y_pos * num_modules_x + x_pos
      
      for c in xrange(num_output_channels):
        deriv[:, c] = derivs[:, offset + c * num_modules_x * num_modules_y]

      d_input = np.dot(deriv, filters)

      for c in xrange(num_input_channels):
        for y in xrange(start_y, start_y + kernel_size_y):
          if y < 0 or y >= image_size_y:
            continue
          for x in xrange(start_x, start_x + kernel_size_x):
            if x < 0 or x >= image_size_x:
              continue
            input_data_x = x - start_x
            input_data_y = y - start_y
            input_data_index = (c * kernel_size_y + input_data_y) * kernel_size_x + input_data_x
            images_index     = (c * image_size_y  +            y) * image_size_x  +            x
            output[:, images_index] += d_input[:, input_data_index]

  return output

def ConvOutp(images, derivs, image_shape, conv_spec, partial_sum_y=0, partial_sum_x=0):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  if partial_sum_x == 0:
    partial_sum_x = num_modules_x
  if partial_sum_y == 0:
    partial_sum_y = num_modules_y
  partial_sum_locs_x = DivUp(num_modules_x, partial_sum_x)
  partial_sum_locs_y = DivUp(num_modules_y, partial_sum_y)
  input_size = kernel_size_y * kernel_size_x * num_input_channels
  output = np.zeros((num_output_channels, input_size), dtype=np.float32)
  output2 = np.zeros((num_output_channels, input_size), dtype=np.float32)
  output_psums = np.zeros((num_output_channels,  input_size * partial_sum_locs_x * partial_sum_locs_y), dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):
      input_data = np.zeros((num_images, input_size), dtype=np.float32)
      deriv_data = np.zeros((num_images, num_output_channels), dtype=np.float32)

      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y
      offset = y_pos * num_modules_x + x_pos

      for c in xrange(num_input_channels):
        for y in xrange(start_y, start_y + kernel_size_y):
          if y < 0 or y >= image_size_y:
            continue
          for x in xrange(start_x, start_x + kernel_size_x):
            if x < 0 or x >= image_size_x:
              continue
            input_data_x = x - start_x
            input_data_y = y - start_y
            input_data_index = (c * kernel_size_y + input_data_y) * kernel_size_x + input_data_x
            images_index     = (c * image_size_y  +            y) * image_size_x  +            x
            input_data[:, input_data_index] = images[:, images_index]

      for c in xrange(num_output_channels):
        deriv_data[:, c] = derivs[:, offset + c * num_modules_x * num_modules_y]

      partial_sum_id_y = y_pos / partial_sum_y
      partial_sum_id_x = x_pos / partial_sum_x
      partial_sum_id = partial_sum_id_y * partial_sum_locs_x + partial_sum_id_x
      outp = np.dot(deriv_data.T, input_data)
      output_psums[:, partial_sum_id * input_size : (partial_sum_id + 1) * input_size] += outp
      output += outp

  for partial_sum_id_y in xrange(partial_sum_locs_y):
    for partial_sum_id_x in xrange(partial_sum_locs_x):
      partial_sum_id = partial_sum_id_y * partial_sum_locs_x + partial_sum_id_x
      output2 += output_psums[:, partial_sum_id * input_size : (partial_sum_id + 1) * input_size]

  if not np.allclose(output2, output):
    print 'Error', np.abs(output - output2).max()
    print output
    print output2

  return output, output_psums


def MaxPool(images, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  output = np.zeros((num_images, num_modules_x * num_modules_y * num_output_channels), dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):

      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y
      offset = y_pos * num_modules_x + x_pos

      for c in xrange(num_input_channels):
        input_data = np.zeros(num_images, dtype=np.float32) - np.inf
        for y in xrange(start_y, start_y + kernel_size_y):
          if y < 0 or y >= image_size_y:
            continue
          for x in xrange(start_x, start_x + kernel_size_x):
            if x < 0 or x >= image_size_x:
              continue
            images_index = (c * image_size_y + y) * image_size_x + x
            input_data = np.maximum(input_data, images[:, images_index])

        output[:, offset + c * num_modules_x * num_modules_y] = input_data
  return output

def MaxPool3D(images, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels, image_size_t = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, kernel_size_t, stride_y, stride_x, stride_t, padding_y, padding_x, padding_t = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  num_modules_t = (image_size_t + 2 * padding_t - kernel_size_t) / stride_t + 1
  output = np.zeros((num_images, num_modules_x * num_modules_y * num_output_channels * num_modules_t), dtype=np.float32)

  for t_pos in xrange(num_modules_t):
    for y_pos in xrange(num_modules_y):
      for x_pos in xrange(num_modules_x):

        start_t = t_pos * stride_t - padding_t
        start_y = y_pos * stride_y - padding_y
        start_x = x_pos * stride_x - padding_x
        offset  = (t_pos * num_output_channels * num_modules_y + y_pos) * num_modules_x + x_pos

        for c in xrange(num_input_channels):
          input_data = np.zeros(num_images, dtype=np.float32) - np.inf
          for t in xrange(start_t, start_t + kernel_size_t):
            if t < 0 or t >= image_size_t:
              continue
            for y in xrange(start_y, start_y + kernel_size_y):
              if y < 0 or y >= image_size_y:
                continue
              for x in xrange(start_x, start_x + kernel_size_x):
                if x < 0 or x >= image_size_x:
                  continue
                images_index = ((t * num_input_channels + c) * image_size_y + y) * image_size_x + x
                input_data = np.maximum(input_data, images[:, images_index])

          output[:, offset + c * num_modules_x * num_modules_y] = input_data
  return output

def AvgPool3D(images, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels, image_size_t = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, kernel_size_t, stride_y, stride_x, stride_t, padding_y, padding_x, padding_t = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  num_modules_t = (image_size_t + 2 * padding_t - kernel_size_t) / stride_t + 1
  output = np.zeros((num_images, num_modules_x * num_modules_y * num_output_channels * num_modules_t), dtype=np.float32)

  for t_pos in xrange(num_modules_t):
    for y_pos in xrange(num_modules_y):
      for x_pos in xrange(num_modules_x):

        start_t = t_pos * stride_t - padding_t
        start_y = y_pos * stride_y - padding_y
        start_x = x_pos * stride_x - padding_x
        offset  = (t_pos * num_output_channels * num_modules_y + y_pos) * num_modules_x + x_pos

        for c in xrange(num_input_channels):
          input_data = np.zeros(num_images, dtype=np.float32)
          region_size = 0
          for t in xrange(start_t, start_t + kernel_size_t):
            if t < 0 or t >= image_size_t:
              continue
            for y in xrange(start_y, start_y + kernel_size_y):
              if y < 0 or y >= image_size_y:
                continue
              for x in xrange(start_x, start_x + kernel_size_x):
                if x < 0 or x >= image_size_x:
                  continue
                images_index = ((t * num_input_channels + c) * image_size_y + y) * image_size_x + x
                input_data += images[:, images_index]
                region_size += 1

          output[:, offset + c * num_modules_x * num_modules_y] = input_data / region_size
  return output

def AvgPool(images, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  output = np.zeros((num_images, num_modules_x * num_modules_y * num_output_channels), dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):

      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y
      offset = y_pos * num_modules_x + x_pos

      for c in xrange(num_input_channels):
        input_data = np.zeros(num_images, dtype=np.float32)
        region_size = 0
        for y in xrange(start_y, start_y + kernel_size_y):
          if y < 0 or y >= image_size_y:
            continue
          for x in xrange(start_x, start_x + kernel_size_x):
            if x < 0 or x >= image_size_x:
              continue
            images_index = (c * image_size_y + y) * image_size_x + x
            input_data += images[:, images_index]
            region_size += 1

        output[:, offset + c * num_modules_x * num_modules_y] = input_data / region_size
  return output

def MaxPoolUndo(images, maxes, derivs, image_shape, deriv_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  output = np.zeros(images.shape, dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):

      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y

      for c in xrange(num_input_channels):
        offset = x_pos + num_modules_x * (y_pos + num_modules_y * c)
        for y in xrange(start_y, start_y + kernel_size_y):
          if y < 0 or y >= image_size_y:
            continue
          for x in xrange(start_x, start_x + kernel_size_x):
            if x < 0 or x >= image_size_x:
              continue
            images_index = (c * image_size_y + y) * image_size_x + x
            for i in xrange(num_images):
              if images[i, images_index] == maxes[i, offset]:
                output[i, images_index] += derivs[i, offset]

  return output

def MaxPoolRprop(images, R_images, maxes, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  output = np.zeros(maxes.shape, dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):

      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y

      for c in xrange(num_input_channels):
        offset = x_pos + num_modules_x * (y_pos + num_modules_y * c)
        for y in xrange(start_y, start_y + kernel_size_y):
          if y < 0 or y >= image_size_y:
            continue
          for x in xrange(start_x, start_x + kernel_size_x):
            if x < 0 or x >= image_size_x:
              continue
            images_index = (c * image_size_y + y) * image_size_x + x
            for i in xrange(num_images):
              if images[i, images_index] == maxes[i, offset]:
                output[i, offset] += R_images[i, images_index]

  return output

def MaxPool3DUndo(images, maxes, derivs, image_shape, deriv_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels, image_size_t = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, kernel_size_t, stride_y, stride_x, stride_t, padding_y, padding_x, padding_t = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  num_modules_t = (image_size_t + 2 * padding_t - kernel_size_t) / stride_t + 1
  output = np.zeros(images.shape, dtype=np.float32)

  for t_pos in xrange(num_modules_t):
    for y_pos in xrange(num_modules_y):
      for x_pos in xrange(num_modules_x):

        start_x = x_pos * stride_x - padding_x
        start_y = y_pos * stride_y - padding_y
        start_t = t_pos * stride_t - padding_t

        for c in xrange(num_input_channels):
          offset  = ((t_pos * num_output_channels + c) * num_modules_y + y_pos) * num_modules_x + x_pos
          for t in xrange(start_t, start_t + kernel_size_t):
            if t < 0 or t >= image_size_t:
              continue
            for y in xrange(start_y, start_y + kernel_size_y):
              if y < 0 or y >= image_size_y:
                continue
              for x in xrange(start_x, start_x + kernel_size_x):
                if x < 0 or x >= image_size_x:
                  continue
                images_index = ((t * num_input_channels + c) * image_size_y + y) * image_size_x + x
                for i in xrange(num_images):
                  if images[i, images_index] == maxes[i, offset]:
                    output[i, images_index] += derivs[i, offset]

  return output

def AvgPool3DUndo(derivs, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels, image_size_t = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, kernel_size_t, stride_y, stride_x, stride_t, padding_y, padding_x, padding_t = conv_spec
  assert (num_output_channels == num_input_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  num_modules_t = (image_size_t + 2 * padding_t - kernel_size_t) / stride_t + 1
  output = np.zeros((num_images, image_size_x * image_size_y * num_input_channels * image_size_t), dtype=np.float32)

  for t_pos in xrange(num_modules_t):
    for y_pos in xrange(num_modules_y):
      for x_pos in xrange(num_modules_x):
        start_x = x_pos * stride_x - padding_x
        start_y = y_pos * stride_y - padding_y
        start_t = t_pos * stride_t - padding_t
   
        end_y = start_y + kernel_size_y
        end_x = start_x + kernel_size_x
        end_t = start_t + kernel_size_t
        start2_y = min(max(start_y, 0), image_size_y)
        start2_x = min(max(start_x, 0), image_size_x)
        start2_t = min(max(start_t, 0), image_size_t)
        end_y = min(max(end_y, 0), image_size_y)
        end_x = min(max(end_x, 0), image_size_x)
        end_t = min(max(end_t, 0), image_size_t)
        region_size = (end_y - start2_y) * (end_x - start2_x) * (end_t - start2_t)

        for c in xrange(num_input_channels):
          offset  = ((t_pos * num_output_channels + c) * num_modules_y + y_pos) * num_modules_x + x_pos
          for t in xrange(start2_t, end_t):
            for y in xrange(start2_y, end_y):
              for x in xrange(start2_x, end_x):
                images_index = ((t * num_input_channels + c) * image_size_y + y) * image_size_x + x
                output[:, images_index] += derivs[:, offset] / region_size
  return output

def AvgPoolUndo(derivs, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, stride_y, stride_x, padding_y, padding_x = conv_spec
  assert (num_input_channels == num_output_channels)
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  output = np.zeros((num_images, image_size_x * image_size_y * num_input_channels), dtype=np.float32)

  for y_pos in xrange(num_modules_y):
    for x_pos in xrange(num_modules_x):
      start_x = x_pos * stride_x - padding_x
      start_y = y_pos * stride_y - padding_y
      
      end_y = start_y + kernel_size_y
      end_x = start_x + kernel_size_x
      start2_y = min(max(start_y, 0), image_size_y)
      start2_x = min(max(start_x, 0), image_size_x)
      end_y = min(max(end_y, 0), image_size_y)
      end_x = min(max(end_x, 0), image_size_x)
      region_size = (end_y - start2_y) * (end_x - start2_x)

      for c in xrange(num_input_channels):
        offset = (c * num_modules_y + y_pos) * num_modules_x + x_pos
        for y in xrange(start2_y, end_y):
          for x in xrange(start2_x, end_x):
            images_index = (c * image_size_y + y) * image_size_x + x
            output[:, images_index] += derivs[:, offset] / region_size

  return output


def GetBounds(i, numF, num_channels, blocked):
  startPos = (i / numF) * numF if blocked else i - numF/2
  endPos = min(startPos + numF, num_channels)
  startPos = max(0, startPos)
  return startPos, endPos

def GetBoundsInv(i, numF, num_channels, blocked):
  """Return the set of filters such that i appears in their normalization group."""
  startPos = (i / numF) * numF if blocked else i - numF + numF/2 + 1
  endPos = min(startPos + numF, num_channels)
  startPos = max(0, startPos)
  return startPos, endPos

def ComputeDenoms(data, numF, blocked, addScale):
  denoms = np.zeros(data.shape, dtype=data.dtype)
  num_images, num_channels = data.shape
  for i in xrange(num_channels):
    startPos, endPos = GetBounds(i, numF, num_channels, blocked)
    for j in xrange(startPos, endPos):
      denoms[:, i] += data[:, j]**2
  denoms = 1 + addScale * denoms
  return denoms

def ResponseNormCrossMap(images, image_shape, numF, add_scale, pow_scale, blocked):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  output = np.zeros((num_images, image_size_x * image_size_y * num_input_channels), dtype=np.float32)
  for y_pos in xrange(image_size_y):
    for x_pos in xrange(image_size_x):
      this_loc_all_channels = np.zeros((num_images, num_input_channels), dtype=np.float32)
      for c in xrange(num_input_channels):
        loc_id = x_pos + image_size_x * (y_pos + image_size_y * c)
        this_loc_all_channels[:, c] = images[:, loc_id]
      denoms = ComputeDenoms(this_loc_all_channels, numF, blocked, add_scale)
      this_loc_all_channels *= np.power(denoms, -pow_scale)
      for c in xrange(num_input_channels):
        loc_id = x_pos + image_size_x * (y_pos + image_size_y * c)
        output[:, loc_id] = this_loc_all_channels[:, c]
  return output

def ResponseNormCrossMapUndo(derivs, images, image_shape, numF, add_scale, pow_scale, blocked):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  output = np.zeros((num_images, image_size_x * image_size_y * num_input_channels), dtype=np.float32)
  for y_pos in xrange(image_size_y):
    for x_pos in xrange(image_size_x):
      this_loc_all_channels_data = np.zeros((num_images, num_input_channels), dtype=np.float32)
      this_loc_all_channels_deriv = np.zeros((num_images, num_input_channels), dtype=np.float32)
      for c in xrange(num_input_channels):
        loc_id = x_pos + image_size_x * (y_pos + image_size_y * c)
        this_loc_all_channels_data[:, c] = images[:, loc_id]
        this_loc_all_channels_deriv[:, c] = derivs[:, loc_id]
      denoms = ComputeDenoms(this_loc_all_channels_data, numF, blocked, add_scale)
      for c in xrange(num_input_channels):
        loc_id = x_pos + image_size_x * (y_pos + image_size_y * c)
        startPos, endPos = GetBoundsInv(c, numF, num_input_channels, blocked)
        output[:, loc_id] = this_loc_all_channels_deriv[:, c] * np.power(denoms[:, c], -pow_scale) \
        - 2 * add_scale * pow_scale * this_loc_all_channels_data[:, c] * \
           (this_loc_all_channels_deriv[:, startPos:endPos] \
            * this_loc_all_channels_data[:, startPos:endPos] \
            * np.power(denoms[:, startPos:endPos], -pow_scale-1)).sum(axis=1)
  return output

def ResponseNormCrossMapRprop(images, derivs, image_shape, numF, add_scale, pow_scale, blocked):
  num_images, image_size_x, image_size_y, num_input_channels = image_shape
  output = np.zeros((num_images, image_size_x * image_size_y * num_input_channels), dtype=np.float32)
  for y_pos in xrange(image_size_y):
    for x_pos in xrange(image_size_x):
      this_loc_all_channels_data = np.zeros((num_images, num_input_channels), dtype=np.float32)
      this_loc_all_channels_deriv = np.zeros((num_images, num_input_channels), dtype=np.float32)
      for c in xrange(num_input_channels):
        loc_id = x_pos + image_size_x * (y_pos + image_size_y * c)
        this_loc_all_channels_data[:, c] = images[:, loc_id]
        this_loc_all_channels_deriv[:, c] = derivs[:, loc_id]
      denoms = ComputeDenoms(this_loc_all_channels_data, numF, blocked, add_scale)
      for c in xrange(num_input_channels):
        loc_id = x_pos + image_size_x * (y_pos + image_size_y * c)
        startPos, endPos = GetBounds(c, numF, num_input_channels, blocked)
        output[:, loc_id] = this_loc_all_channels_deriv[:, c] * np.power(denoms[:, c], -pow_scale) \
        - 2 * add_scale * pow_scale * this_loc_all_channels_data[:, c] * \
        np.power(denoms[:, c], -pow_scale-1) * \
           (this_loc_all_channels_deriv[:, startPos:endPos] \
            * this_loc_all_channels_data[:, startPos:endPos]).sum(axis=1)
  return output




def ConvUp3D(images, filters, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels, image_size_t = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, kernel_size_t, stride_y, stride_x, stride_t, padding_y, padding_x, padding_t = conv_spec
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  num_modules_t = (image_size_t + 2 * padding_t - kernel_size_t) / stride_t + 1
  output = np.zeros((num_images, num_modules_x * num_modules_y * num_output_channels * num_modules_t), dtype=np.float32)

  for t_pos in xrange(num_modules_t):
    for y_pos in xrange(num_modules_y):
      for x_pos in xrange(num_modules_x):
        input_data = np.zeros((num_images, kernel_size_x * kernel_size_y * num_input_channels * kernel_size_t), dtype=np.float32)

        start_x = x_pos * stride_x - padding_x
        start_y = y_pos * stride_y - padding_y
        start_t = t_pos * stride_t - padding_t

        for c in xrange(num_input_channels):
          for t in xrange(start_t, start_t + kernel_size_t):
            if t < 0 or t >= image_size_t:
              continue
            for y in xrange(start_y, start_y + kernel_size_y):
              if y < 0 or y >= image_size_y:
                continue
              for x in xrange(start_x, start_x + kernel_size_x):
                if x < 0 or x >= image_size_x:
                  continue
                input_data_x = x - start_x
                input_data_y = y - start_y
                input_data_t = t - start_t
                input_data_index = ((input_data_t * num_input_channels + c) * kernel_size_y + input_data_y) * kernel_size_x + input_data_x
                images_index     = ((t * num_input_channels + c) * image_size_y + y) * image_size_x + x
                input_data[:, input_data_index] = images[:, images_index]
        output_data = np.dot(input_data, filters.T)

        for c in xrange(num_output_channels):
          offset = ((t_pos * num_output_channels + c) * num_modules_y + y_pos) * num_modules_x + x_pos
          output[:, offset] = output_data[:, c]
  return output

def ConvDown3D(derivs, filters, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels, image_size_t = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, kernel_size_t, stride_y, stride_x, stride_t, padding_y, padding_x, padding_t = conv_spec
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  num_modules_t = (image_size_t + 2 * padding_t - kernel_size_t) / stride_t + 1
  output = np.zeros((num_images, image_size_x * image_size_y * num_input_channels * image_size_t), dtype=np.float32)

  for t_pos in xrange(num_modules_t):
    for y_pos in xrange(num_modules_y):
      for x_pos in xrange(num_modules_x):
        deriv = np.zeros((num_images, num_output_channels), dtype=np.float32)
        
        start_x = x_pos * stride_x - padding_x
        start_y = y_pos * stride_y - padding_y
        start_t = t_pos * stride_t - padding_t
        
        for c in xrange(num_output_channels):
          offset = ((t_pos * num_output_channels + c) * num_modules_y + y_pos) * num_modules_x + x_pos
          deriv[:, c] = derivs[:, offset]

        d_input = np.dot(deriv, filters)

        for c in xrange(num_input_channels):
          for t in xrange(start_t, start_t + kernel_size_t):
            if t < 0 or t >= image_size_t:
              continue
            for y in xrange(start_y, start_y + kernel_size_y):
              if y < 0 or y >= image_size_y:
                continue
              for x in xrange(start_x, start_x + kernel_size_x):
                if x < 0 or x >= image_size_x:
                  continue
                input_data_x = x - start_x
                input_data_y = y - start_y
                input_data_t = t - start_t
                input_data_index = ((input_data_t * num_input_channels + c) * kernel_size_y + input_data_y) * kernel_size_x + input_data_x
                images_index     = ((t * num_input_channels + c) * image_size_y + y) * image_size_x + x
                output[:, images_index] += d_input[:, input_data_index]
  return output

def ConvOutp3D(images, derivs, image_shape, conv_spec):
  num_images, image_size_x, image_size_y, num_input_channels, image_size_t = image_shape
  num_output_channels, kernel_size_y, kernel_size_x, kernel_size_t, stride_y, stride_x, stride_t, padding_y, padding_x, padding_t = conv_spec
  num_modules_y = (image_size_y + 2 * padding_y - kernel_size_y) / stride_y + 1
  num_modules_x = (image_size_x + 2 * padding_x - kernel_size_x) / stride_x + 1
  num_modules_t = (image_size_t + 2 * padding_t - kernel_size_t) / stride_t + 1

  input_size = kernel_size_y * kernel_size_x * num_input_channels * kernel_size_t
  output = np.zeros((num_output_channels, input_size), dtype=np.float32)

  for t_pos in xrange(num_modules_t):
    for y_pos in xrange(num_modules_y):
      for x_pos in xrange(num_modules_x):
        input_data = np.zeros((num_images, input_size), dtype=np.float32)
        deriv = np.zeros((num_images, num_output_channels), dtype=np.float32)

        start_x = x_pos * stride_x - padding_x
        start_y = y_pos * stride_y - padding_y
        start_t = t_pos * stride_t - padding_t

        for c in xrange(num_input_channels):
          for t in xrange(start_t, start_t + kernel_size_t):
            if t < 0 or t >= image_size_t:
              continue
            for y in xrange(start_y, start_y + kernel_size_y):
              if y < 0 or y >= image_size_y:
                continue
              for x in xrange(start_x, start_x + kernel_size_x):
                if x < 0 or x >= image_size_x:
                  continue
                input_data_x = x - start_x
                input_data_y = y - start_y
                input_data_t = t - start_t
                input_data_index = ((input_data_t * num_input_channels + c) * kernel_size_y + input_data_y) * kernel_size_x + input_data_x
                images_index     = ((t * num_input_channels + c) * image_size_y + y) * image_size_x + x
                input_data[:, input_data_index] = images[:, images_index]

        for c in xrange(num_output_channels):
          offset = ((t_pos * num_output_channels + c) * num_modules_y + y_pos) * num_modules_x + x_pos
          deriv[:, c] = derivs[:, offset]

        output += np.dot(deriv.T, input_data)

  return output
