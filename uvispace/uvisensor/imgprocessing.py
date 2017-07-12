#!/usr/bin/env python
"""This module contains the Image class, for image processing operations.

The operations implemented in the class methods are focused to the 
images obtained from the external FPGAs in the UviSpace project. Thus, 
once obtained a grey scale image, this module provide functions for 
getting the shapes (triangles) in the image, and then their vertices. 
Prior to segment the image, a binarization has to be applied, as it 
eases the segmentation process. 

Important note
--------------

A point array is written by convention in the form 
*[row, column]*. In a cartesian system, the points are expressed
as *(x,y)*. Finally, in an image representation (viewer), the typical is 
to display points coordinates as  *(x', y')*. They equivalences are the 
following:

.. math::

 x = x' = column

 y = -y' = -row

Thus, special care has to be taken when dealing with operations in 
different scopes e.g. trigonometric operations will be handled with the 
cartesian values, while image operations are normally performed with the
array convention. Finally, when sending the array values to a viewer or 
to an external device, the image representation mentioned above is 
the typical used system.
"""
# Standard libraries
import logging
import sys
# Third party libraries
import cv2
import numpy as np
import skimage.measure
import skimage.morphology
# Local libraries
import geometry

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger("sensor")


class Image(object):
    """Class with image processing methods oriented to UGV detection.
        
    :param np.array image: original grey scale image.   
    :param list contours: each element is an Mx2 array containing M 
     points defining a closed contour.
    """

    def __init__(self, image, contours=[]):
        """
        Image class constructor. Set image and contours attributes.
        """
        self.image = image
        self._binarized = None
        self.triangles = []
        self.contours = contours

    def binarize(self, thresholds):
        """Get a binarized image from a grey image given the thresholds.
        
        The input image can only have one dimension. This method is 
        intended to work with 3-component threshold values stored in a
        single 30-bit register:
        
            * *register[0 to 10]* : red component thresholds
            * *register[10 to 20]* : green component thresholds
            * *register[10 to 30]* : blue component thresholds
            
        The raw binary image contains a lot of noise. As it is very low
        around the triangles, masks around them are used to get rid of 
        the noise in the rest of the image.

        :param [int or float, int or float] thresholds : minimum and 
         maximum values between whom the image intensity values will be
         accepted as 1 (rescaled to 255). Values greater than the 
         maximum and smaller than the minimum will be truncated to 0.
        
        :return bin_image: Image of the same size as the input image 
         with only 255 or 0 values (Equivalent to 1 and 0), according 
         to the input threshold values.
        :rtype: binary numpy.array(shape=MxN)
        """
        # Obtain the thresholds in base 2 and get the red component slice.
        th_min = bin(thresholds[0])
        th_max = bin(thresholds[1])
        red_c = (th_min[-30:-20], th_max[-30:-20])
        # Why is it necessary to divide by 4??
        thr_min = int(red_c[0], 2) / 4
        thr_max = int(red_c[1], 2) / 4
        logger.debug("Thresholding between {} and {}"
                     .format(thr_min, thr_max))
        # The first binary approach is obtained evaluating 2 thresholds
        raw_binarized = cv2.inRange(self.image, thr_min, thr_max)
        # A simple erosion gets rid of the whole noise. Dilating the eroded
        # image several times provides an acceptable ROI for the binary mask.
        kernel = np.ones((5, 5), np.uint8)
        erosion = cv2.erode(raw_binarized, kernel, iterations=1)
        kernel = np.ones((5, 5), np.uint8)
        dilate = cv2.dilate(erosion, kernel, iterations=5)
        mask = dilate / 255
        filtered = raw_binarized * mask
        # Eliminate holes inside the detected shapes
        labels = skimage.morphology.label(filtered)
        label_count = np.bincount(labels.ravel())
        # Detect the background pixels, assuming they are majority in the image.
        background = np.argmax(label_count)
        self._binarized = filtered
        self._binarized[labels != background] = 255
        logger.debug("Image binarization finished")
        return self._binarized

    def correct_distortion(self, kx=0.035, ky=0.035, only_contours=True):
        """Correct barrel distortion on contours or on the whole image.
        
        The distortion is corrected using a 2nd polynomial equation for
        every pixel with coordinates :math:`(X_d, Y_d)`. The resulting 
        corrected coordinates :math:`(X_u, Y_u)` are obtained with the 
        following equations:
        
        .. math::

           X_u &=(X_d - C_x) * (1 + k_x * r^2) + C_x \\

           Y_u &= (Y_d - C_y) * (1 + k_y * r^2) + C_y \\

           r  &= [(X_d - C_x)^2 + (Y_d - C_y)^2] / [(C_x^2 + C_y^2) * 2]
        
        :param float kx: X-Axe Distortion coefficient of the lens.
        :param float ky: Y-Axe Distortion coefficient of the lens.
        :param bool only_contours: Specify if the correction is to be 
         applied to the whole image or only to the contours.
        """
        # Calculate the image center as the middle point of the width and height
        center = np.array(self.image.shape) / 2
        # If contours is an empty list, algorithm is not outperformed.
        if only_contours and self.contours:
            for index, cnt in enumerate(self.contours):
                distance = cnt - center
                # Calculate the r distance. First numerator and then denominator
                r = (distance ** 2).sum(axis=1).astype(np.float)
                r /= (center ** 2).sum() * 2
                coeffs = np.array([r*ky, r*kx]).transpose() + 1
                corrected = distance * coeffs + center
                self.contours[index] = corrected
        elif not only_contours:
            pass

    def get_shapes(self, tolerance=8, get_contours=True):
        """Get the shapes' vertices in the binarized image.

        Update the *self.triangles* attribute.

        The shape is obtained using the *Marching Cubes Algorithm*.
        Once obtained, the vertices are calculated using the 
        *Ramer-Douglas-Peucker Algorithm*. Both are implemented on the 
        *skimage* library, and there is more information on its docs.
        
        if the kwarg *get_contours* if False, it is assumed that the 
        contours are already known (stored in variable *self.contours*). 
        If this is the case, the marching cubes algorithm is omitted.

        :param float tolerance: minimum distance between an observed 
         pixel and the previous vertices pixels required to add the 
         first one to the vertices list.
        :param bool get_contours: specify if the *Marching Cubes 
         Algorithm* is applied to the binarized image. Specifically set 
         to False when the binarization algorithm is implemented in the 
         external device (i.e. the FPGA).
        :return: vertices of the N shapes detected on the
         image. each element contains an Mx2 *np.rray* with the 
         coordinates of the M vertices of the shape.
        :rtype: list
        """
        logger.debug("Getting the shapes' vertices in the image")
        # Obtain a list with all the contours in the image, separating each
        # shape in a different element of the list
        if get_contours:
            self.contours = skimage.measure.find_contours(self._binarized, 200)
        self.triangles = []
        # Get the vertices of each shape in the image.
        for cnt in self.contours:
            coords = skimage.measure.approximate_polygon(cnt, tolerance)
            max_coords = np.array(self.image.shape) - 1
            # Sometimes, the initial vertex is repeatead at the end.
            # Thus, if len is 3 and vertex is NOT repeated, it is a triangle
            if len(coords) == 3 and (not np.array_equal(coords[0], coords[-1])):
                triangle = geometry.Triangle(
                        np.clip(coords, [0,0], max_coords))
                self.triangles.append(triangle)
            # If len is 4 and vertex IS repeated, it is a triangle
            if len(coords) == 4 and np.array_equal(coords[0], coords[-1]):
                triangle = geometry.Triangle(np.clip(coords[1:],
                                                     [0,0], max_coords))
                self.triangles.append(triangle)
            logger.debug("A {}-vertices shape was found".format(len(coords)))
        return self.triangles
