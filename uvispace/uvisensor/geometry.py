#!/usr/bin/env python
"""This module contain classes and methods with geometrical operations.

The operations are done in the 2-D space
It works with 2-D shapes represented by arrays. Thus, the calculations
are based on matrix operations and linear algebra. 
"""
# Third party libraries
import numpy as np


class Triangle(object):
    """Class for dealing with geometric operations referred to triangles.

    An instance of the class represents an isosceles triangle in a 
    2-D space, with the 2 equal sides being bigger than the base one.

    :param np.array(shape=3x2) vertices: vertices coordinates of the 
     triangle object.
    :param bool isglobal: Flag that indicates if the coordinate system 
     refers to the 4-quadrant system (global) or to a local quadrant 
     system.
    :param bool cartesian: This flag indicates if the coordinates are 
     referred to a cartesian system [x,y] instead of the images typical 
     standard [row. column] = [y,x]
    """

    def __init__(self, vertices, isglobal=False, cartesian=False):
        """Triangle class constructor."""
        if len(vertices) is not 3:
            raise ValueError("Expected an array with 3 vertices")
        self.vertices = vertices.astype(np.float32)
        # These flags indicate the coordinates system that is being used
        self.isglobal = isglobal
        self.cartesian = cartesian
        # The barycenter X is equal to the sum of the X coordinates divided by 3
        self.barycenter = self.vertices.sum(axis=0) / 3
        self.sides = np.zeros([3])
        # base_index is the identifier for the base side in 'sides' array.
        self.base_index = None
        self.midpoint = np.array([])
        self.angle = None
        self.window = np.array([])
        self.contours = []
        # Scale ratio for converting pixel coordinates to millimetres.
        self._scale = 1

    def __str__(self):
        return "Triangle\n{}".format(self.vertices)

    def __repr__(self):
        return "Triangle\n{}".format(self.vertices)

    def local2global(self, offsets, K=None, image2cartesian=True):
        """Convert Triangle coordinates to the global coordinates system.

        The function performs 2 transformations:

        * Obtains the 4-quadrant coordinates. The input is a coordinate 
          for a 1-quadrant system, and the output corresponds to the 
          4-quadrant system.
        * Move y-axis origin. Initially, for a given image the origin
          is placed at its top. However, for the used system the origin 
          is placed at the middle of the 4 quadrants.

        If indicated, the coordinates system will be transformed to the
        cartesian one. This is recommended, as the image system does not
        make sense for a space with origin in the middle.

        Only absolute coordinates shall be transformed. Lengths and 
        angles are invariant to the coordinates origin.

        Finally, a scale ratio *K* will be applied to the coordinates. 
        The coordinates will be directly multiplied by the ratio.

        :param offsets: column and row offsets between the local and the
          global systems.
        :type offsets: list[int, int]
        :param K: Scale ratio to be applied to the points coordinates.
        :type K: positive int or float
        :param bool image2cartesian: If True, a conversion from image 
         coordinate system to cartesian system is performed. Thus, the 
         output will be of the form of [x,y] instead of [row,column].
        :raises ValueError: if the scale ratio is negative.
        """
        if self.isglobal:
            return
        # Assess K and assign value to 'scale' attribute if it is valid.
        if K is None:
            K = self._scale
        elif K <= 0:
            raise ValueError("The scale ratio K must be greater than 0")
        else:
            self._scale = K
        self.vertices[:,0] = offsets[0] - self.vertices[:,0]
        self.vertices[:,1] -= offsets[1]
        self.vertices *= self._scale
        self.barycenter[0] = offsets[0] - self.barycenter[0]
        self.barycenter[1] -= offsets[1]
        self.barycenter *= self._scale
        # If the pose was not previously calculated,
        # a ValueError is caught and ignored.
        try:
            self.midpoint[0] = offsets[0] - self.midpoint[0]
            self.midpoint[1] -= offsets[1]
            self.midpoint *= self._scale
        except IndexError:
            pass
        if image2cartesian:
            # Convert the vertices coordinates
            tmp = np.copy(self.vertices[:,0])
            self.vertices[:,0] = self.vertices[:,1]
            self.vertices[:,1] = tmp
            # Convert the barycenter coordinates
            tmp = np.copy(self.barycenter[0])
            self.barycenter[0] = self.barycenter[1]
            self.barycenter[1] = tmp
            # Convert the midpoint coordinates
            try:
                tmp = np.copy(self.midpoint[0])
                self.midpoint[0] = self.midpoint[1]
                self.midpoint[1] = tmp
            except IndexError:
                pass
            self.cartesian = True
        self.isglobal = True

    def global2local(self, offsets, K=None, cartesian2image=True):
        """Convert Triangle coordinates to the local coordinates system.
        
        Only absolute coordinates shall be transformed. Lengths and 
        angles are invariant to the coordinate origin.
    
        :param offsets: column and row offsets between the local and the
          global systems.
        :type offsets: list[int, int]
        :param K: Scale ratio to be applied to the points coordinates.
        :type K: positive int or float
        :param bool cartesian2image: If True, a conversion from 
         cartesian coordinates system to image system is performed. 
         Thus, the  output will be of the form of [row,column] instead 
         of [x,y].
        :raises ValueError: if the scale ratio is negative.         
        """
        if not self.isglobal:
            return
        # Assess K and assign value to 'scale' attribute if it is valid.
        if K is None:
            K = self._scale
        elif K <= 0:
            raise ValueError("The scale ratio K must be greater than 0")
        else:
            self._scale = K
        if cartesian2image:
            # Convert the vertices coordinates
            tmp = np.copy(self.vertices[:,0])
            self.vertices[:,0] = self.vertices[:,1]
            self.vertices[:,1] = tmp
            # Convert the barycenter coordinates
            tmp = np.copy(self.barycenter[0])
            self.barycenter[0] = self.barycenter[1]
            self.barycenter[1] = tmp
            # Convert the midpoint coordinates
            try:
                tmp = np.copy(self.midpoint[0])
                self.midpoint[0] = self.midpoint[1]
                self.midpoint[1] = tmp
            except IndexError:
                pass
            self.cartesian = False
        self.vertices /= self._scale
        self.vertices[:,0] = offsets[0] - self.vertices[:,0]
        self.vertices[:,1] += offsets[1]
        self.barycenter /= self._scale
        self.barycenter[0] = offsets[0] - self.barycenter[0]
        self.barycenter[1] += offsets[1]
        # If the pose was not previously calculated,
        # a ValueError is catched and ignored.
        try:
            self.midpoint /= self._scale
            self.midpoint[0] = offsets[0] - self.midpoint[0]
            self.midpoint[1] += offsets[1]
        except IndexError:
            pass
        self.isglobal = False

    def get_pose(self):
        """Return triangle's angle and base midpoint, given its vertices.

        The coordinates of 3 vertices defining the triangle are used,
        packed in a single 3x2 array. This method assumes that the
        triangle is isosceles and the 2 equal sides are bigger than 
        the different one, called base.

        The following attributes are updated:

        * self.sides : array containing the lengths of the 3 sides.
        * self.base_index : array index of the minor side. This is also
          the index of the vertex between the 2 mayor sides, as vertices
          indexes are the indexes of their opposite sides.

        :return: [X,Y] coordinate of 
         the midpoint of the triangle's base side and orientation angle 
         of the triangle. It is the resulting angle between the 
         horizontal axis and the segment that goes from the triangle's 
         midpoint to the frontal vertex. It is expressed in radians, in 
         the range [-pi, pi].
        :rtype: float32, float32, float32
        """
        vertices = self.vertices.astype(np.float32)
        # Calculate the length of the sides i.e. the Euclidean distance
        self.sides[0] = np.linalg.norm(vertices[2] - vertices[1])
        self.sides[1] = np.linalg.norm(vertices[0] - vertices[2])
        self.sides[2] = np.linalg.norm(vertices[1] - vertices[0])
        # If 2 sides are equal, the common vertex is the front one and
        # The base midpoint is calculated with the other 2.
        self.base_index = np.argmin(self.sides)
        self.midpoint = (vertices[self.base_index-1]
                         + vertices[self.base_index-2]) / 2
        # Calculus of the x and y distance between the midpoint and the vertex
        # opposite to the base side.
        if self.cartesian:
            x, y = vertices[self.base_index] - self.midpoint
        else:
            # The array 'y'(rows) counts downwards, contrary to cartesian system
            row, col = vertices[self.base_index] - self.midpoint
            x, y = col, -row
        self.angle = np.arctan2(y, x)
        return self.midpoint[0], self.midpoint[1], self.angle

    def get_window(self, min_value, max_value, k=1.25):
        """Get the coordinates of a rectangle window around the triangle.
        
        At first, the barycenter of the triangle is calculated. Then, 
        the window is calculated as a square, being its sides' length  
        *k* times the triangle's longest side length and being its 
        center the triangle's barycenter. The output is stored in the 
        *self.window* variable

        :param min_value: value or values of the minimum allowed 
         coordinates.
        :param max_value: value or values of the maximum allowed 
         coordinates.
        :param k: relative size between the window and the triangle 
         base. It should be bigger than 1. As bigger as it gets, the 
         bigger the window will be.
        :type min_value: int or np.array[int,int]
        :type max_value: int or np.array[int,int]
        :type k: int or float
        :return: array representing a square parallel to the horizontal 
         coordinates axe. The first row contains the X and Y minimum
         values of the square, and the second row contains its X and Y 
         maximum values.
        :rtype: 2x2 np.array
        """
        distance = self.sides.max() * k
        window = np.array([self.barycenter - distance,
                           self.barycenter + distance])
        # Create 2 arrays of booleans: the first indicating if any value in each
        # axis is greater than max_value, and the second if any value in each
        # axis is lower than min_value.
        outbounds = [np.any(window - max_value > 0, axis=0),
                     np.any(window - min_value < 0, axis=0)]
        # Third condition array, when none of the previous ones is fulfilled.
        inbounds = np.all(np.invert(outbounds), axis=0)
        condlist = np.vstack([outbounds, inbounds])
        # Subtract to each axis the greatest distance from one of its pixels
        # to the maximum allowed. Idem for the minimum values.
        max_clipped = window - np.max(window - max_value, axis=0)
        min_clipped = window + np.max(min_value - window, axis=0)
        choicelist = [max_clipped, min_clipped, window]
        # Obtain the final array getting elements from each of the 3 values
        # arrays, depending on the conditions values.
        self.window = np.select(condlist, choicelist)
        return self.window

    def homography(self, H):
        """Perform an homography operation to the Triangle vertices.

        The homography is a geometrical transformation that obtains the 
        projection of certain points from a plain to another. 
        *self.vertices* variable is updated

        :param H: Homography matrix.
        :type H: np.array(shape=3x3)
        :return: the new vertices coordinates values.
        """
        points = np.copy(self.vertices)
        # Loop for performing the homography to every 2-D vertex' coordinates.
        for index, row in enumerate(points):
            # Append '1' to the point vector and perform a matrix product with H
            operand = np.hstack([row, 1])
            product = np.dot(H, operand)
            new_point = product[0:2] / product[2]
            points[index] = new_point
        self.vertices = np.copy(points)
        return self.vertices

    def inverse_homography(self, H):
        """Perform an inverse homography operation to the vertices.

        Get :math:`X_u` from the equation 
        :math:`(w \\cdot X) = H \\cdot Y`.

        First of all, get :math:`\\frac{1}{w \\cdot Y}` using least 
        squares method. Then, extracts :math:`\\frac{1}{w}` from the 
        column matrix, with the hypothesis that :math:`Y_{11} = 1`.

        :param H: Homography matrix.
        :type H: np.array(shape=3x3)
        :return: the new vertices coordinates values.
        """
        points = np.copy(self.vertices)
        # Loop for performing the homography to every 2-D vertex' coordinates.
        for index, row in enumerate(points):
            # Append '1' to the point vector and perform a matrix product with H
            operand = np.hstack([row, 1])
            # Use least squares method to get Y from X=H.Y
            product = np.linalg.lstsq(H, operand)[0]
            new_point = product[0:2] / product[2]
            points[index] = new_point
        self.vertices = np.copy(points)
        return self.vertices

    def in_borders(self, limits, tolerance=150):
        """Evaluate if vertices are near a 4-sides polygon perimeter.

        In the real world scenario, this method determines if the UGV, 
        represented by the *Triangle*, is in the borders region of a 
        given 2-D space, defined by an irregular 4-sides polygon.

        :param limits: Array containing the coordinates of the 4 points
         defining the borders of the polygon.
        :param tolerance: Maximum allowed distance (mm) to the limits 
         to be considered within the borders region.
        :type limits: iterable of length 4
        :type tolerance: int or float
        :return: flag set to True if the triangle is evaluated to be 
         inside the given polygon
        :rtype: bool
        """
        for index in range(len(limits)):
            # Define a segment with 2 limit points of the quadrant.
            seg = Segment(limits[index], limits[index - 1])
            # Evaluate each vertex of the triangle.
            for vertex in self.vertices:
                # Get the distance in mm to the segment.
                dist = seg.distance2point(vertex)
                # Evaluate if the vertex is closer than the tolerance.
                if dist < tolerance:
                    return True
        # If any of the vertices wasn't near to any of the segments
        # return False.
        return False


class Segment(object):
    """This class contains methods for dealing with 2D segments operations.

    :param point_a: X and Y coordinates of the initial points.
    :param point_b: X and Y coordinates of the  end points.
    :type point_a: len-2 tuple or list
    :type point_b: len-2 tuple or list
    """

    def __init__(self, point_a, point_b):
        """Define the segment basic attributes."""
        self.pointA = np.array(point_a)
        self.pointB = np.array(point_b)
        # Get the segment modulus for further operations.
        self.modulus = np.linalg.norm(self.pointA - self.pointB)

    def distance2point(self, point):
        """Return the distance of a point to the nearest segment's point.

        The calculus is based on the dot (scalar) product. The
        perpendicular projection of a first vector on a second one is
        the dot product the 2 vectors divided by the modulus of the 
        second:

        .. math::

           A.B = |A| \\cdot |B| \cdot cos(alpha) 

        being :math:`|A| \\cdot cos(alpha)` the projection of A on B

        If the projection is less than 0, it implies that the point is
        left to the first point (as cos(alpha) is negative), being this
        first point the nearest one to the target point. 

        Moreover, if the projection is greater than the modulus of the
        segment, it implies that the target point is is right to the end
        point, being this the nearest one.

        Finally, the the distance to the segment is obtained and 
        returned using the Pythagoras' theorem.

        :return: The distance of the point to the segment
        """
        # target point and Segment's final point coordinates referred to the
        # initial point. Needed for the dot product.
        vector1 = self.pointB - self.pointA
        vector2 = point - self.pointA
        # Distance from pointA to the projection of vector2 on vector1.
        projection = np.dot(vector1, vector2) / self.modulus
        # Case that target point is minor that pointA
        if projection <= 0:
            distance = np.linalg.norm(vector2)
        # Case that target point is greater that pointB
        elif projection >= self.modulus:
            distance = np.linalg.norm(point - self.pointB)
        # Case that target point is between pointA and pointB
        else:
            # Pythagoras theorem for getting the leg of a right-angled triangle.
            distance = np.sqrt((vector2 ** 2).sum() - projection ** 2)
        return distance
