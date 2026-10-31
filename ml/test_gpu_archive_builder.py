import unittest
from build_gpu_archive_dataset import clean_boxes,compatible_yolo,fractional_box,source_split
class ArchiveDatasetTests(unittest.TestCase):
 def test_person_mapping_and_background(self):
  self.assertEqual(compatible_yolo('0 .5 .5 .2 .4',{0}),[[.5,.5,.2,.4]])
  self.assertEqual(compatible_yolo('',{0}),[])
  with self.assertRaises(ValueError):compatible_yolo('2 .5 .5 .2 .4',{0})
 def test_bad_boxes_never_become_empty_labels(self):
  for text in ['0 .99 .5 .5 .4','0 .5 .5 -.2 .4','0 nan .5 .2 .4','0 .5 .5']:
   with self.assertRaises(ValueError):compatible_yolo(text,{0})
 def test_pixel_conversion_and_clipping(self):
  self.assertEqual(fractional_box(10,20,20,40,100,100),[.2,.4,.2,.4])
  self.assertEqual(fractional_box(-10,0,20,100,100,100),[.05,.5,.1,1.0])
  with self.assertRaises(ValueError):fractional_box(110,0,20,10,100,100)
 def test_source_test_split_is_explicit(self):
  self.assertEqual(source_split('test/images/a.jpg'),'test')
  self.assertEqual(source_split('valid/images/a.jpg'),'val')
  self.assertIsNone(source_split('unknown/images/a.jpg'))
